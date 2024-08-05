import os
import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from datetime import date, timedelta, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import calendar

# Load environment variables from .env file
load_dotenv()

# Access environment variables from .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

SET_DATE, SET_TIME, SET_CITY = range(3)

# Timezone for scheduling (change as per your requirement)
TIMEZONE = 'Asia/Kolkata'

# Dictionary to store user settings (time and city)
user_settings = {}

# Scheduler object
scheduler = BackgroundScheduler()

# Function to get weather data
def get_weather(city):
    url = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": {"message": "Failed to retrieve weather data. Please try again later."}}

# Function to format the weather message
def format_weather_message(data):
    city = data["location"]["name"]
    current_temp_c = data["current"]["temp_c"]
    weather_description = data["current"]["condition"]["text"].lower()
    
    if "sunny" in weather_description:
        return (f"☀️ Current Weather in {city}:\n\n"
                f"It's a bright and sunny day with a temperature of {current_temp_c}°C. Perfect weather to soak up some sunshine and enjoy the outdoors! 🌞")
    elif "cloudy" in weather_description:
        return (f"☁️ Current Weather in {city}:\n\n"
                f"The temperature is {current_temp_c}°C, with a blanket of clouds overhead. A great day for a cozy indoor activity or a leisurely walk! ☁️")
    elif any(keyword in weather_description for keyword in ["rain", "showers"]):
        return (f"🌧️ Current Weather in {city}:\n\n"
                f"It's {current_temp_c}°C with rain showers. Don’t forget your umbrella if you're heading out, and maybe enjoy the soothing sound of the rain! 🌧️")
    elif "snow" in weather_description:
        return (f"❄️ Current Weather in {city}:\n\n"
                f"Brrr, it’s {current_temp_c}°C with a snowy wonderland outside. Bundle up if you're going out, or stay warm and watch the snowflakes dance! ❄️")
    elif "windy" in weather_description:
        return (f"🌬️ Current Weather in {city}:\n\n"
                f"The temperature is {current_temp_c}°C, and it's quite windy out there. Hold onto your hat and enjoy the brisk breeze! 🌬️")
    elif any(keyword in weather_description for keyword in ["storm", "thunderstorm"]):
        return (f"⛈️ Current Weather in {city}:\n\n"
                f"It's {current_temp_c}°C with a storm brewing. Stay safe indoors, and perhaps enjoy a good book or movie while the storm passes! ⛈️")
    elif "fog" in weather_description:
        return (f"🌫️ Current Weather in {city}:\n\n"
                f"With a temperature of {current_temp_c}°C, it's quite foggy. Drive safely and take it slow in the low visibility! 🌫️")
    elif "partly cloudy" in weather_description:
        return (f"🌤️ Current Weather in {city}:\n\n"
                f"The temperature is {current_temp_c}°C with some clouds in the sky. It's a mix of sun and clouds, perfect weather for a day outdoors! 🌤️")
    elif "overcast" in weather_description:
        return (f"🌥️ Current Weather in {city}:\n\n"
                f"It's {current_temp_c}°C with overcast skies. The sky is completely covered with clouds, making it a bit gloomy outside. 🌥️")
    elif "mist" in weather_description:
        return (f"🌫️ Current Weather in {city}:\n\n"
                f"The temperature is {current_temp_c}°C with mist in the air. The visibility is reduced, so take care if you're driving or walking outdoors! 🌫️")
    else:
        return (f"Current Weather in {city}:\n\n"
                f"The temperature is {current_temp_c}°C with {weather_description}.")

def send_daytime_alert(context):
    current_time = datetime.now(pytz.timezone(TIMEZONE)).time()

    # Check if current time is between 8 AM and 8 PM
    if current_time >= time(8, 0) and current_time <= time(20, 0):
        # Iterate through user settings
        for user_id in user_settings:
            # Get user's city preference
            city = user_settings[user_id]['city']

            # Fetch weather data for the user's city
            weather_data = get_weather(city)

            # Check for errors in weather data retrieval
            if "error" in weather_data:
                message = f"Error: {weather_data['error']['message']}"
            else:
                # Format the weather message using the retrieved data
                message = format_weather_message(weather_data)

            # Send the formatted weather message to the user
            context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
    else:
        print("Skipping daytime alert as it is outside of specified hours.")

# Function to send weather update message
def send_weather_update(context):
    for user_id, settings in user_settings.items():
        city = settings['city']
        weather_data = get_weather(city)
        if "error" in weather_data:
            message = f"Error: {weather_data['error']['message']}"
        else:
            message = format_weather_message(weather_data)
        context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)

# Function to handle /setweather command
def set_weather(update, context):
    update.message.reply_text("Please select the date for your weather update:", reply_markup=get_date_keyboard(datetime.now().year, datetime.now().month))
    return SET_DATE

# Function to generate a calendar keyboard for date selection
def get_date_keyboard(year, month):
    keyboard = []
    days = calendar.monthcalendar(year, month)
    for week in days:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Next Month >>", callback_data=f"next_month_{year}_{month}")])
    return InlineKeyboardMarkup(keyboard)

# Function to handle date selection
def date_handler(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data.startswith("next_month"):
        year, month = map(int, query.data.split("_")[2:])
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        query.edit_message_text(text="Please select the date:", reply_markup=get_date_keyboard(year, month))
    else:
        year, month, day = map(int, query.data.split("_")[1:])
        selected_date = date(year, month, day)
        context.user_data['selected_date'] = selected_date
        query.edit_message_text(text=f"Selected date: {selected_date}. Please select the time for your weather update:", reply_markup=get_time_keyboard())
        return SET_TIME

# Function to generate a time keyboard for hour selection
def get_time_keyboard():
    keyboard = []
    for hour in range(24):
        row = []
        for minute in [0, 15, 30, 45]:
            row.append(InlineKeyboardButton(f"{hour:02}:{minute:02}", callback_data=f"time_{hour}_{minute}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# Function to handle time selection
def time_handler(update, context):
    query = update.callback_query
    query.answer()
    
    hour, minute = map(int, query.data.split("_")[1:])
    selected_time = f"{hour:02}:{minute:02}"
    context.user_data['selected_time'] = selected_time
    
    query.edit_message_text(text=f"Selected time: {selected_time}. Please enter your city name:")
    return SET_CITY

# Function to handle city input
def city_handler(update, context):
    user_id = update.message.from_user.id
    city = update.message.text.strip()
    context.user_data['city'] = city
    
    # Store user settings
    user_settings[user_id] = {
        'time': context.user_data['selected_time'],
        'city': city
    }
    
    update.message.reply_text(f"Weather updates set for {context.user_data['selected_date']} at {context.user_data['selected_time']} for city {city}.")
    schedule_weather_update(context)
    return ConversationHandler.END

# Function to handle /stopweather command
def stop_weather(update, context):
    user_id = update.message.from_user.id
    if user_id in user_settings:
        del user_settings[user_id]
        update.message.reply_text("You will no longer receive daily weather updates.")
    else:
        update.message.reply_text("You haven't set any daily weather updates yet.")

def schedule_weather_update(context):
    global scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)
        scheduler = BackgroundScheduler()
    
    scheduler.configure(timezone=pytz.timezone(TIMEZONE))
    
    for user_id, settings in user_settings.items():
        time_str = settings['time']
        city = settings['city']
        
        hour, minute = map(int, time_str.split(':'))
        
        # Schedule weather update for each user
        weather_trigger = CronTrigger(hour=hour, minute=minute, timezone=pytz.timezone(TIMEZONE))
        scheduler.add_job(send_weather_update, trigger=weather_trigger, args=[context])
        
        # Schedule daytime alert every 4 hours
        daytime_trigger = CronTrigger(hour='*/4', timezone=pytz.timezone(TIMEZONE))
        scheduler.add_job(send_daytime_alert, trigger=daytime_trigger, args=[context])
    
    scheduler.start()

# Function to handle the /start command
def start(update, context):
    update.message.reply_text(f"Hello {update.message.from_user.first_name}! 🌞\n\n"
                              "Welcome to our weather bot, created by a team of passionate engineering students from DSCE. Whether you're planning a picnic, checking on your travel destinations, or simply curious about the weather, I'm here to help!\n\n"
                              "To set your daily weather update time and city, use the command:\n"
                              "/setweather\n\n"
                              "To stop receiving daily weather updates, use:\n"
                              "/stopweather\n\n"
                              "Let's dive into the world of weather! 🌍☀️🌧️❄️")

# Function to handle messages
def message_handler(update, context):
    text = update.message.text.strip().lower()
    if text.startswith("/setweather"):
        set_weather(update, context)
    elif text == "/stopweather":
        stop_weather(update, context)
    else:
        update.message.reply_text("I don't understand that command. Please use /setweather to set daily weather updates or /stopweather to stop them.")

# Define the main function to start the bot
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setweather', set_weather)],
        states={
            SET_DATE: [CallbackQueryHandler(date_handler, pattern='^date_|next_month')],
            SET_TIME: [CallbackQueryHandler(time_handler, pattern='^time_')],
            SET_CITY: [MessageHandler(Filters.text & ~Filters.command, city_handler)]
        },
        fallbacks=[CallbackQueryHandler(date_handler, pattern='^ignore$')],
        allow_reentry=True
    )

    dp.add_handler(conv_handler)
    
    # Command handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('stopweather', stop_weather))

    # Message handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    scheduler.start()

    # Start the bot
    updater.start_polling()
    print("Telegram bot is now running.")

    # Keep the program running
    updater.idle()

if __name__ == '__main__':
    main()
import datetime
import random
import asyncio
import os
from aiohttp import web
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TIME_OPTIONS = [
    "19:00", "19:30", "20:00", "20:30", "21:00", "22:00", "22:30", "23:00"
]
MAX_PLAYERS = 10

def shuffle_players(players):
    random.shuffle(players)
    return players[:5], players[5:10]


async def start(update, context):
    context.user_data['chat_id'] = update.effective_chat.id
    context.user_data['reminder_task'] = None
    keyboard = [[InlineKeyboardButton("Сыграть", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Саломалейкум, {update.message.from_user.username}! Хуш омади ба боти Counter-Organizer by Комил Муминов",
        reply_markup=reply_markup)


async def join_game(update, context):
    username = update.callback_query.from_user.username
    if username in context.user_data.get('players', []):
        return await update.callback_query.answer("Вы уже в списке игроков!")

    context.user_data.setdefault('players', []).append(username)
    available_players = len(context.user_data['players'])

    if available_players == MAX_PLAYERS:
        team1, team2 = shuffle_players(context.user_data['players'])
        await update.callback_query.message.reply_text(
            f"Игра начнется в {context.user_data['game_start_time']}\n\nСписок игроков:\n"
            + "\n".join(context.user_data['players']) +
            f"\n\nКоманды:\nКоманда 1: {', '.join(team1)}\nКоманда 2: {', '.join(team2)}"
        )

    await update.callback_query.answer(
        f"Вы присоединились к игре! ({available_players}/{MAX_PLAYERS})")
    await update.callback_query.edit_message_text(
        f"Список игроков ({available_players}/{MAX_PLAYERS}):\n" +
        "\n".join(context.user_data['players']) +
        f"\nВремя игры: {context.user_data.get('game_start_time', 'Не выбрано')}"
    )

    if context.user_data['players'][0] == username:
        keyboard = [[
            InlineKeyboardButton(time, callback_data=time)
            for time in TIME_OPTIONS
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(
            "Выберите время игры:", reply_markup=reply_markup)


async def set_game_time(update, context):
    context.user_data['game_start_time'] = update.callback_query.data
    await update.callback_query.edit_message_text(
        f"Время игры установлено на {context.user_data['game_start_time']}.\n\nСписок игроков:\n"
        + "\n".join(context.user_data['players']))
    await update.callback_query.answer()

    # Подтверждение участия
    keyboard = [[
        InlineKeyboardButton("Подтвердить участие", callback_data='confirm_participation')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Подтвердите свое участие в игре:", reply_markup=reply_markup)

    # Напоминание об игре
    await schedule_reminder(update, context)

    # Уведомление всех игроков
    for player in context.user_data['players']:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"{player}, игра запланирована на {context.user_data['game_start_time']}!")


async def confirm_participation(update, context):
    username = update.callback_query.from_user.username
    context.user_data.setdefault('confirmed_players', []).append(username)

    confirmed = len(context.user_data['confirmed_players'])
    await update.callback_query.answer("Ваше участие подтверждено!")
    await update.callback_query.edit_message_text(
        f"Подтверждено игроков: {confirmed}/{MAX_PLAYERS}.\n" +
        "\n".join(context.user_data['confirmed_players']))


async def schedule_reminder(update, context):
    game_time = datetime.datetime.strptime(context.user_data['game_start_time'], "%H:%M")
    now = datetime.datetime.now()
    game_datetime = now.replace(hour=game_time.hour, minute=game_time.minute, second=0)

    # Вычисляем оставшееся время до игры
    reminder_time = game_datetime - datetime.timedelta(minutes=15)
    delay = (reminder_time - now).total_seconds()

    if delay > 0:
        if context.user_data['reminder_task']:
            context.user_data['reminder_task'].cancel()

        context.user_data['reminder_task'] = asyncio.create_task(remind_players(context, delay))
    else:
        await remind_players(context, 0)


async def remind_players(context, delay):
    await asyncio.sleep(delay)
    players = context.user_data.get('players', [])
    for player in players:
        await context.bot.send_message(
            chat_id=context.user_data['chat_id'],
            text=f"{player}, напоминание! Игра начнется через 15 минут."
        )


async def change_game_time(update, context):
    if context.user_data['players'][0] != update.callback_query.from_user.username:
        await update.callback_query.answer("Только лидер игры может изменить время!")
        return

    keyboard = [[
        InlineKeyboardButton(time, callback_data=time) for time in TIME_OPTIONS
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Выберите новое время для игры:", reply_markup=reply_markup)
    await update.callback_query.answer()


async def cancel_game(update, context):
    if context.user_data['players'][0] != update.callback_query.from_user.username:
        await update.callback_query.answer("Только лидер игры может отменить игру!")
        return

    # Уведомление всех игроков
    for player in context.user_data.get('players', []):
        await context.bot.send_message(
            chat_id=context.user_data['chat_id'],
            text=f"{player}, игра была отменена."
        )

    # Очистка данных
    context.user_data['players'] = []
    context.user_data['game_start_time'] = None
    if context.user_data.get('reminder_task'):
        context.user_data['reminder_task'].cancel()

    await update.callback_query.edit_message_text(
        "Игра была отменена. Все участники удалены из списка.")

    keyboard = [[InlineKeyboardButton("Сыграть", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Новая игра. Нажмите на кнопку, чтобы присоединиться.",
        reply_markup=reply_markup)


# Функция для запуска бота на Vercel
async def handle(request):
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(join_game, pattern="join_game"))
    application.add_handler(CallbackQueryHandler(set_game_time, pattern="|".join(TIME_OPTIONS)))
    application.add_handler(CallbackQueryHandler(confirm_participation, pattern="confirm_participation"))
    application.add_handler(CallbackQueryHandler(change_game_time, pattern="change_time"))
    application.add_handler(CallbackQueryHandler(cancel_game, pattern="cancel_game"))

    # Запуск бота на Vercel
    await application.updater.start_polling()

    return web.Response(text="Bot is running")


# Создание веб-сервера для Vercel
app = web.Application()
app.add_routes([web.get('/', handle)])

# Запуск сервера
if __name__ == "__main__":
    web.run_app(app)

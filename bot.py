import datetime
import random
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, filters

TIME_OPTIONS = [
    "19:00", "19:30", "20:00", "20:30", "21:00", "22:00", "22:30", "23:00"
]
MAX_PLAYERS = 10


def shuffle_players(players):
    random.shuffle(players)
    return players[:5], players[5:10]


async def start(update, context):
    context.user_data['chat_id'] = update.effective_chat.id
    keyboard = [[InlineKeyboardButton("Сыграть", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Саломалейкум, {update.message.from_user.username}! Хуш омади ба боти Counter-Organaizer by Комил Муминов",
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

    keyboard = [[
        InlineKeyboardButton("Изменить время", callback_data='change_time')
    ], [InlineKeyboardButton("Отменить игру", callback_data='cancel_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Вы можете изменить время игры или отменить игру.",
        reply_markup=reply_markup)


async def change_game_time(update, context):
    if context.user_data['players'][
            0] != update.callback_query.from_user.username:
        await update.callback_query.answer(
            "Только лидер игры может изменить время!")
        return

    keyboard = [[
        InlineKeyboardButton(time, callback_data=time) for time in TIME_OPTIONS
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Выберите новое время для игры:", reply_markup=reply_markup)
    await update.callback_query.answer()


async def cancel_game(update, context):
    if context.user_data['players'][
            0] != update.callback_query.from_user.username:
        await update.callback_query.answer(
            "Только лидер игры может отменить игру!")
        return

    context.user_data['players'] = []
    context.user_data['game_start_time'] = None
    await update.callback_query.edit_message_text(
        "Игра была отменена. Все участники удалены из списка.")

    keyboard = [[InlineKeyboardButton("Сыграть", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "Новая игра. Нажмите на кнопку, чтобы присоединиться.",
        reply_markup=reply_markup)


def main():
    application = Application.builder().token(
        "7312402670:AAEgb72S8pIWWdsxDYK17d-nmLTB5PYxI0I").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(join_game, pattern="join_game"))
    application.add_handler(
        CallbackQueryHandler(set_game_time, pattern="|".join(TIME_OPTIONS)))
    application.add_handler(
        CallbackQueryHandler(change_game_time, pattern="change_time"))
    application.add_handler(
        CallbackQueryHandler(cancel_game, pattern="cancel_game"))

    application.run_polling()


if __name__ == "__main__":
    main()

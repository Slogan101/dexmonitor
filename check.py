import asyncio
import os
import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes
from io import BytesIO

from funct import (
    load_sent_file, save_sent_file, make_token_signature, is_token_already_sent,
    load_boosted_tokens, save_boosted_tokens, make_boost_signature, is_boost_already_sent,
    load_trending_tokens, save_trending_tokens, make_trending_signature, is_trend_already_sent,
    token_age, value_number, load_registered_chats, save_registered_chats
)

from dotenv import load_dotenv


load_dotenv()

LATEST_TOKEN_PROFILES = os.environ.get("LATEST_TOKEN_PROFILES")
TOKEN_PROFILE_NAMES = os.environ.get("TOKEN_PROFILE_NAMES")
LATEST_BOOST = os.environ.get("LATEST_BOOST")
TRENDING_TOKENS = os.environ.get("TRENDING_TOKENS")
registered_groups = load_registered_chats()




async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        channel_chat = update.channel_post.chat
        channel_id = channel_chat.id
        if channel_id not in registered_groups:
            registered_groups.add(channel_id)
            save_registered_chats(registered_groups)
            await context.bot.send_message(chat_id=channel_id, text="✅ Registered this channel for token alerts.")
        else:
            await context.bot.send_message(chat_id=channel_id, text="ℹ️ This Channel is already registered.")



async def get_latest_tokens(update: Update, context: CallbackContext):
    response = requests.get(LATEST_TOKEN_PROFILES)
    tokens = tokens = response.json()

    sent_tokens = await load_sent_file()
    new_tokens = []


    for tok in tokens:
        token_address = tok.get("tokenAddress", "Unknown")
        chain_id = tok.get("chainId", "Unknown")
        chart = tok.get("url", "Unknown")
        header = tok.get("header", "Unknown")

        # Defaults
        name = symbol = main_vol = main_liq = main_cap = age = "N/A"
        volume_24h = liquidity_usd = market_cap = created_at = "N/A"

        try:
            name_resp = requests.get(f"{TOKEN_PROFILE_NAMES}/{token_address}")
            if name_resp.status_code == 200:
                name_data = name_resp.json()
                pairs = name_data.get("pairs", [])
                if pairs:
                    pair = pairs[0]
                    base_token = pair.get("baseToken", {})
                    name = base_token.get("name", "Unknown")
                    symbol = base_token.get("symbol", "Unknown")
                    volume_24h = pair.get("volume", {}).get("h24", 0)
                    main_vol = value_number(volume_24h)
                    liquidity_usd = pair.get("liquidity", {}).get("usd", 0)
                    main_liq = value_number(liquidity_usd)
                    market_cap = pair.get("marketCap", 0)
                    main_cap = value_number(market_cap)
                    created_at = pair.get("pairCreatedAt", 0)
                    age = token_age(created_at)
        except Exception as e:
            print(f"Error processing token {token_address}: {e}")

        signature = make_token_signature(name, token_address, symbol, chain_id)

        if is_token_already_sent(signature, sent_tokens):
            print(f"⏭️ Already sent Token: {name} [{token_address}]")
            continue

        links = tok.get("links", [])
        if links:
            link_lines = []
            for link in links:
                label = link.get("label") or link.get("type", "Unknown").capitalize()
                url = link.get("url", "No URL")
                link_lines.append(f"<a href='{url}'>{label}</a>")
            links_text = " | ".join(link_lines)
        else:
            links_text = "None"

        message = (
            f"🚨🚨🚨<b>Token Alert🚨🚨🚨</b>\n\n"
            f"🔵 <b>{name} [{symbol}] [{chain_id}]</b>\n\n"
            f"<code>{token_address}</code>\n\n"
            f"🌱 Age: {age} | 💰 MC: <code>${main_cap}</code>\n💧 Liq: <code>${main_liq}</code> | 📈 24H Vol: <code>${main_vol}</code>\n\n"
            f"📊<a href='{chart}'>Chart</a>\n\n"
            f"🔗 <b>{links_text}</b>"
        )
        if header != "Unknown":
            for chat_id in registered_groups:
                try:
                    image_response = requests.get(header)
                    image_bytes = BytesIO(image_response.content)
                    image_bytes.name = "token_header.png"
                    await context.bot.send_photo(chat_id=chat_id, photo=image_bytes, caption=message, parse_mode=ParseMode.HTML)
                    new_tokens.append(signature)
                    await asyncio.sleep(4)
                except Exception as e:
                    print(f"Error sending to {chat_id}: {e}")
            else:
                continue

    if new_tokens:
        save_sent_file(new_tokens)



async def get_latest_boost(context: CallbackContext):
    boosts = requests.get(LATEST_BOOST).json()
    sent_boosts = await load_boosted_tokens()
    new_boosts = []

    for tok in boosts:
        token_address = tok.get("tokenAddress", "Unknown")
        chain_id = tok.get("chainId", "Unknown")
        chart = tok.get("url", "Unknown")
        header = tok.get("header", "Unknown")
        total_boosts = tok.get("totalAmount", 0)
        recent_boosts = tok.get("amount", 0)

        try:
            name_resp = requests.get(f"{TOKEN_PROFILE_NAMES}/{token_address}")
            if name_resp.status_code == 200:
                name_data = name_resp.json()
                pairs = name_data.get("pairs", [])
                name = pairs[0].get("baseToken", {}).get("name", "Unknown") if pairs else "Unknown"
            else:
                name = "Unknown"
        except Exception:
            name = "Unknown"

        signature = make_boost_signature(name, token_address, chain_id, recent_boosts, total_boosts)
        if is_boost_already_sent(signature, sent_boosts):
            print(f"⏭️ Skipped already sent boost: {name} [{token_address}]")
            continue

        links = tok.get("links", [])
        if links:
            link_lines = []
            for link in links:
                label = link.get("label") or link.get("type", "Unknown").capitalize()
                url = link.get("url", "No URL")
                link_lines.append(f"<a href='{url}'>{label}</a>")
            links_text = " | ".join(link_lines)
        else:
            links_text = "None"

        message = (
            f"🚀🚀🚀<b>New Boost Alert🚀🚀🚀</b>\n\n"
            f"🔵 <b>{name} [{chain_id}]</b>\n\n"
            f"<code>{token_address}</code>\n\n"
            f"<b>Boosts</b>: {recent_boosts} (Total: {total_boosts})\n\n"
            f"📊<a href='{chart}'>Chart</a>\n"
            f"🔗 <b>{links_text}</b>"
        )

        if header != "Unknown":
            for chat_id in registered_groups:
                try:
                    image_response = requests.get(header)
                    image_bytes = BytesIO(image_response.content)
                    image_bytes.name = "token_header.png"
                    await context.bot.send_photo(chat_id=chat_id, photo=image_bytes, caption=message, parse_mode=ParseMode.HTML)
                    new_boosts.append(signature)
                    await asyncio.sleep(4)
                except Exception as e:
                    print(f"Error sending to {chat_id}: {e}")
            else:
                continue

    if new_boosts:
        await save_boosted_tokens(new_boosts)



async def get_trending(update: Update, context: CallbackContext):
    trending = requests.get(TRENDING_TOKENS).json()
    sent_trends = await load_trending_tokens()
    new_trends = []


    for tok in trending:
        token_address = tok.get("tokenAddress", "Unknown")

        chain_id = tok.get("chainId", "Unknown")
        chart = tok.get("url", "Unknown")
        header = tok.get("header", "Unknown")

        name = symbol = main_vol = main_liq = main_cap = age = "N/A"
        volume_24h = liquidity_usd = market_cap = created_at = "N/A"

        try:
            name_resp = requests.get(f"{TOKEN_PROFILE_NAMES}/{token_address}")
            if name_resp.status_code == 200:
                name_data = name_resp.json()
                pairs = name_data.get("pairs", [])
                if pairs:
                    pair = pairs[0]
                    base_token = pair.get("baseToken", {})
                    name = base_token.get("name", "Unknown Name")
                    symbol = base_token.get("symbol", "Unknown Symbol")
                    volume_24h = pair.get("volume", {}).get("h24", 0)
                    main_vol = value_number(volume_24h)
                    liquidity_usd = pair.get("liquidity", {}).get("usd", 0)
                    main_liq = value_number(liquidity_usd)
                    market_cap = pair.get("marketCap", 0)
                    main_cap = value_number(market_cap)
                    created_at = pair.get("pairCreatedAt", 0)
                    age = token_age(created_at)
        except Exception as e:
            print(f"Error processing trending token {token_address}: {e}")

        signature = make_trending_signature(name, token_address, symbol, chain_id)

        if is_trend_already_sent(signature, sent_trends):
            print(f"⏭️ Already sent trend: {name} [{token_address}]")
            continue

        links = tok.get("links", [])
        if links:
            link_lines = []
            for link in links:
                label = link.get("label") or link.get("type", "Unknown").capitalize()
                url = link.get("url", "No URL")
                link_lines.append(f"<a href='{url}'>{label}</a>")
            links_text = " | ".join(link_lines)
        else:
            links_text = "None"

        message = (
            f"🚨<b>Trending</b>🚨\n\n"
            f"🔵<b>{name} [{symbol}] [{chain_id}]</b>\n\n"
            f"<code>{token_address}</code>\n\n"
            f"🌱 Age: {age} | 💰 MC: <code>${main_cap}</code>\n💧 Liq: <code>${main_liq}</code> | 📈 24H Vol: <code>${main_vol}</code>\n\n"
            f"📊<a href='{chart}'>Chart</a>\n"
            f"🔗 <b>{links_text}</b>"
        )

        if header != "Unknown":
            for chat_id in registered_groups:
                try:
                    image_response = requests.get(header)
                    image_bytes = BytesIO(image_response.content)
                    image_bytes.name = "token_header.png"
                    await context.bot.send_photo(chat_id=chat_id, photo=image_bytes, caption=message, parse_mode=ParseMode.HTML)
                    new_trends.append(signature)
                    await asyncio.sleep(4)
                except Exception as e:
                    print(f"Error sending to {chat_id}: {e}")
            else:
                continue

    if new_trends:
        await save_trending_tokens(new_trends)




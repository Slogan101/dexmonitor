import os
import asyncio
import requests
from telegram import Update, ChatMember, Chat
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes
from functions import (load_sent_file, load_boosted_tokens, make_boost_signature, make_token_signature, is_boost_already_sent,
is_token_already_sent, save_sent_file, save_boosted_tokens, load_registered_chats, save_registered_chats, value_number, token_age, is_trend_already_sent,
load_trending_tokens, make_trending_signature, save_trending_tokens)
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
            
 



# Latest token profiles
async def get_latest_tokens(update: Update, context: CallbackContext):
    response = requests.get(LATEST_TOKEN_PROFILES)
    tokens = response.json()
    sent_tokens = await load_sent_file()
    new_tokens = []


    for tok in tokens:
        token_info = {}
        token_address = tok.get("tokenAddress", "Unknown")
        chain_id = tok.get("chainId", "Unknown")
        # amount = tok.get("amount", 0)  # boost amount

        token_info['address'] = token_address
        token_info['chainId'] = chain_id

         # Initialize variables with default values
        name = symbol = main_vol = main_liq = main_cap = age = "N/A"

        # Fetch name
        try:
            name_resp = requests.get(f"{TOKEN_PROFILE_NAMES}/{token_address}")
            if name_resp.status_code == 200:
                name_data = name_resp.json()
                pairs = name_data.get("pairs", [])
                if pairs:
                    pair = pairs[0]  # Get the first trading pair

                    base_token = pair.get("baseToken", {})
                    name = base_token.get("name", "Unknown Name")
                    symbol = base_token.get("symbol", "Unknown Symbol")

                    # Price
                    # price_usd = pair.get("priceUsd", "N/A")
                    # price_native = pair.get("priceNative", "N/A")

                    # Volume
                    volume_24h = pair.get("volume", {}).get("h24", "N/A")
                    main_vol = value_number(volume_24h)

                    # Liquidity
                    liquidity_usd = pair.get("liquidity", {}).get("usd", "N/A")
                    main_liq = value_number(liquidity_usd)

                    # Market Cap
                    market_cap = pair.get("marketCap", "N/A")
                    main_cap = value_number(liquidity_usd)

                    # Pair creation time
                    created_at = pair.get("pairCreatedAt", "N/A")
                    age = token_age(created_at)

        except Exception as e:
            print(f"Error processing token {token_address}: {e}")

        # Build signature and check if already sent
        signature = make_token_signature(name, token_address, symbol, chain_id, volume_24h, liquidity_usd, market_cap, created_at)
        if is_token_already_sent(signature, sent_tokens):
            print(f"⏭️ Already sent Token: {name} [{token_address}]")
            continue  # skip already sent

        # Social links
        links = tok.get("links", [])
        if links:
            link_lines = []
            for link in links:
                label = link.get("label") or link.get("type", "Unknown").capitalize()
                url = link.get("url", "No URL")
                link_lines.append(f"<a href='{url}'>{label}</a>")
            links_text = "\n".join(link_lines)
        else:
            links_text = "None"

        message = (
            f"🚨🚨🚨<b>Token Alert🚨🚨🚨</b>\n\n"
            f"🔵 <b>{name} [{symbol}] [{chain_id}]</b>\n\n"
            f"<code>{token_address}</code>\n\n"
            f"🌱 Age: {age} | 💰 MC: <code>${main_cap}</code>\n💧 Liq: <code>${main_liq}</code> | 📈 24H Vol: <code>${main_vol}</code>\n\n"
            f"🔗 <b>Social Links:</b>\n{links_text}"
        )


        for chat_id in registered_groups:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
                new_tokens.append(signature)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error sending to {chat_id}: {e}")
        if new_tokens:
            sent_tokens.extend(new_tokens)
            save_sent_file(sent_tokens)



    




async def get_latest_boost(context: CallbackContext):
    boosts = requests.get(LATEST_BOOST)
    boosts = boosts.json()
    sent_boosts = await load_boosted_tokens()
    new_boosts = []

    for tok in boosts:
        token_address = tok.get("tokenAddress", "Unknown")
        chain_id = tok.get("chainId", "Unknown")
        total_boosts = tok.get("totalAmount", 0)
        recent_boosts = tok.get("amount", 0)

        # Get token name
        try:
            name_resp = requests.get(f"{TOKEN_PROFILE_NAMES}/{token_address}")
            if name_resp.status_code == 200:
                name_data = name_resp.json()
                pairs = name_data.get("pairs", [])
                if pairs:
                    base_token = pairs[0].get("baseToken", {})
                    name = base_token.get("name", "Unknown Name")
                else:
                    name = "Unknown"
            else:
                name = "Unknown"
        except Exception:
            name = "Unknown"

        # Create signature
        signature = make_boost_signature(name, token_address, chain_id, recent_boosts, total_boosts)
        if is_boost_already_sent(signature, sent_boosts):
            print(f"⏭️ Skipped already sent boost: {name} [{token_address}]")
            continue  # Skip duplicates

        # Social links
        links = tok.get("links", [])
        if links:
            link_lines = []
            for link in links:
                label = link.get("label") or link.get("type", "Unknown").capitalize()
                url = link.get("url", "No URL")
                link_lines.append(f"<a href='{url}'>{label}</a>")
            links_text = "\n".join(link_lines)
        else:
            links_text = "None"

        message = (
            f"🚀🚀🚀<b>New Boost Alert🚀🚀🚀</b>\n\n"
            f"🏷️ Token Name: <b>{name} [{chain_id}]</b>\n\n"
            f"<code>{token_address}</code>\n\n"
            f"<b>Boosts</b>: {recent_boosts} (Total: {total_boosts})\n\n"
            f"🔗 <b>Social Links:</b>\n{links_text}"
        )

        for chat_id in registered_groups:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
                new_boosts.append(signature)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error sending to {chat_id}: {e}")

    # Save updated boost list
        if new_boosts:
            sent_boosts.extend(new_boosts)
            await save_boosted_tokens(sent_boosts)




async def get_trending(update: Update, context: CallbackContext):
    trending = requests.get(TRENDING_TOKENS)
    trending = trending.json()
    sent_trends = await load_trending_tokens()
    new_trends = []

    for trends in trending:
        chain_id = trends.get("chainId", "Unknown")
        token_address = trends.get("tokenAddress", "Unknown")

        # Initialize variables with default values
        name = symbol = main_vol = main_liq = main_cap = age = "N/A"

        try:
            name_resp = requests.get(f"{TOKEN_PROFILE_NAMES}/{token_address}")
            if name_resp.status_code == 200:
                name_data = name_resp.json()
                pairs = name_data.get("pairs", [])
                if pairs:
                    pair = pairs[0]  # Get the first trading pair

                    base_token = pair.get("baseToken", {})
                    name = base_token.get("name", "Unknown Name")
                    symbol = base_token.get("symbol", "Unknown Symbol")

                    # Price
                    # price_usd = pair.get("priceUsd", "N/A")
                    # price_native = pair.get("priceNative", "N/A")

                    # Volume
                    volume_24h = pair.get("volume", {}).get("h24", "N/A")
                    main_vol = value_number(volume_24h)

                    # Liquidity
                    liquidity_usd = pair.get("liquidity", {}).get("usd", "N/A")
                    main_liq = value_number(liquidity_usd)

                    # Market Cap
                    market_cap = pair.get("marketCap", "N/A")
                    main_cap = value_number(liquidity_usd)

                    # Pair creation time
                    created_at = pair.get("pairCreatedAt", "N/A")
                    age = token_age(created_at)

        except Exception as e:
            print(f"Error processing token {token_address}: {e}")
        
        signature = make_trending_signature(name, token_address, symbol, chain_id, volume_24h, liquidity_usd, market_cap, created_at)
        if is_trend_already_sent(signature, sent_trends):
            print(f"⏭️ Skipped already sent Trends: {name} [{token_address}]")
            continue  # Skip duplicates

        links = trends.get("links", [])
        if links:
            link_lines = []
            for link in links:
                label = link.get("label") or link.get("type", "Unknown").capitalize()
                url = link.get("url", "No URL")
                link_lines.append(f"<a href='{url}'>{label}</a>")
            links_text = "\n".join(link_lines)
        else:
            links_text = "None"

        
        message = (
            f"🚨<b>Trending </b>🚨\n\n"
            f"🔵<b>{name} [{symbol}] [{chain_id}]</b>\n\n"
            f"<code>{token_address}</code>\n\n"
            f"🌱 Age: {age} | 💰 MC: <code>${main_cap}</code>\n💧 Liq: <code>${main_liq}</code> | 📈 24H Vol: <code>${main_vol}</code>\n\n"
            f"🔗 <b>Social Links:</b>\n{links_text}"
        )

        for chat_id in registered_groups:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
                new_trends.append(signature)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error sending to {chat_id}: {e}")
        if new_trends:
            new_trends.extend(new_trends)
            await save_trending_tokens(new_trends)

 




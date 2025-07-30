import json
import os
import datetime

MAX_TOKENS = 2000
SENT_TOKENS_FILE = "sent_tokens.json"
BOOST_SENT_FILE = "sent_boost.json"
SENT_TRENDS_FILE = "sent_trends.json"
CHAT_FILE = "registered_chats.json"


# =================== UTILITIES ===================9

def replace_or_add(signature, existing_signatures):
    replaced = False
    for i, entry in enumerate(existing_signatures):
        if entry["tokenAddress"] == signature["tokenAddress"] and entry["chainId"] == signature["chainId"]:
            # Check if values differ
            if entry != signature:
                existing_signatures[i] = signature  # Update existing
                replaced = True
            return existing_signatures, replaced
    existing_signatures.append(signature)
    return existing_signatures, True  # New entry added


# =================== TOKENS ===================

async def load_sent_file():
    if not os.path.exists(SENT_TOKENS_FILE):
        return []
    with open(SENT_TOKENS_FILE, "r") as f:
        return json.load(f)


def save_sent_file(new_tokens):
    existing_tokens = []
    if os.path.exists(SENT_TOKENS_FILE):
        try:
            with open(SENT_TOKENS_FILE, "r") as f:
                existing_tokens = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Warning: Corrupted sent_tokens.json. Resetting.")

    for token in new_tokens:
        existing_tokens, _ = replace_or_add(token, existing_tokens)

    trimmed = existing_tokens[-MAX_TOKENS:]
    with open(SENT_TOKENS_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


def is_token_already_sent(signature, sent_signatures):
    for entry in sent_signatures:
        if entry["tokenAddress"] == signature["tokenAddress"] and entry["chainId"] == signature["chainId"]:
            return entry == signature  # True if identical
    return False


def make_token_signature(name, token_address, symbol, chain_id, volume_24h, liquidity_usd, market_cap, created_at):
    return {
        "name": name,
        "tokenAddress": token_address,
        "symbol": symbol,
        "chainId": chain_id,
        "volume": volume_24h,
        "liquidity": liquidity_usd,
        "marketCap": market_cap,
        "pairCreatedAt": created_at
    }

# =================== BOOSTED ===================

async def load_boosted_tokens():
    if not os.path.exists(BOOST_SENT_FILE):
        return []
    with open(BOOST_SENT_FILE, "r") as f:
        return json.load(f)


async def save_boosted_tokens(new_tokens):
    existing = []
    if os.path.exists(BOOST_SENT_FILE):
        try:
            with open(BOOST_SENT_FILE, "r") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Warning: Corrupted boost file. Resetting.")

    for token in new_tokens:
        existing, _ = replace_or_add(token, existing)

    trimmed = existing[-MAX_TOKENS:]
    with open(BOOST_SENT_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


def make_boost_signature(name, token_address, chain_id, amount=0, totalAmount=0):
    return {
        "name": name,
        "tokenAddress": token_address,
        "chainId": chain_id,
        "amount": amount,
        "totalAmount": totalAmount
    }


def is_boost_already_sent(signature, sent_list):
    for entry in sent_list:
        if entry["tokenAddress"] == signature["tokenAddress"] and entry["chainId"] == signature["chainId"]:
            return entry == signature
    return False

# =================== TRENDING ===================

async def load_trending_tokens():
    if not os.path.exists(SENT_TRENDS_FILE):
        return []
    with open(SENT_TRENDS_FILE, "r") as f:
        return json.load(f)


async def save_trending_tokens(new_tokens):
    existing = []
    if os.path.exists(SENT_TRENDS_FILE):
        try:
            with open(SENT_TRENDS_FILE, "r") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Warning: Corrupted trends file. Resetting.")

    for token in new_tokens:
        existing, _ = replace_or_add(token, existing)

    trimmed = existing[-MAX_TOKENS:]
    with open(SENT_TRENDS_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


def make_trending_signature(name, token_address, symbol, chain_id, volume_24h, liquidity_usd, market_cap, created_at):
    return {
        "name": name,
        "tokenAddress": token_address,
        "symbol": symbol,
        "chainId": chain_id,
        "volume": volume_24h,
        "liquidity": liquidity_usd,
        "marketCap": market_cap,
        "pairCreatedAt": created_at
    }


def is_trend_already_sent(signature, sent_list):
    for entry in sent_list:
        if entry["tokenAddress"] == signature["tokenAddress"] and entry["chainId"] == signature["chainId"]:
            return entry == signature
    return False

# =================== CHATS ===================

def load_registered_chats():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_registered_chats(chat_ids):
    with open(CHAT_FILE, "w") as f:
        json.dump(list(chat_ids), f)

# =================== MISC ===================

def token_age(ms_timestamp):
    try:
        created_time = datetime.datetime.fromtimestamp(ms_timestamp / 1000)
        now = datetime.datetime.now()
        delta = now - created_time

        if delta.days >= 1:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"
    except Exception:
        return "N/A"


def value_number(num):
    try:
        num = float(num)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.2f}K"
        else:
            return f"{num:.2f}"
    except Exception:
        return "N/A"

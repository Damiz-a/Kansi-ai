import re
import math
import random


GREETINGS = [
    "Hello! I'm Kansi AI. How are you feeling today?",
    "Hi there! I'm here to listen. What's on your mind?",
    "Hey! Welcome. How can I support you today?",
]

EMPATHY_SAD = [
    "I hear you, and your feelings are completely valid. Would you like to tell me more about what's going on?",
    "That sounds really tough. I'm here to listen — take your time.",
    "I'm sorry you're feeling this way. You don't have to go through it alone. Would you like to talk about it?",
]

EMPATHY_ANXIOUS = [
    "Anxiety can feel so overwhelming. Try taking a slow, deep breath with me. Would you like to share what's worrying you?",
    "I understand that feeling. Your worries are valid. What's been on your mind?",
    "It's okay to feel anxious. Let's take this one step at a time. What would help right now?",
]

EMPATHY_HAPPY = [
    "That's wonderful to hear! What's been making you feel good?",
    "I'm so glad! Celebrating positive moments matters. Tell me more!",
    "That's lovely! Holding onto these moments is important.",
]

FALLBACK = [
    "Thank you for sharing that. Would you like to tell me more?",
    "I appreciate you opening up. How does that make you feel?",
    "That's interesting. Is there anything specific I can help you with?",
]

ABOUT_ME = (
    "I'm Kansi AI, a mental health screening companion. I can chat with you about how you're feeling, "
    "answer general questions, do maths, and analyse text for emotional patterns. "
    "I'm not a therapist — for serious concerns, please speak with a professional."
)


def solve_math(expr):
    expr = expr.strip()
    expr = re.sub(r'[^0-9\+\-\*\/\.\(\)\s\^]', '', expr)
    expr = expr.replace('^', '**')
    if not expr:
        return None
    try:
        allowed = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sqrt": math.sqrt, "pi": math.pi, "e": math.e,
        }
        result = eval(expr, {"__builtins__": {}}, allowed)
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return str(result)
    except Exception:
        return None


def respond(message, user_name="Friend"):
    msg = message.strip()
    lower = msg.lower()

    if not msg:
        return "I'm here whenever you're ready to talk."

    math_only = re.match(r'^[\d\s\+\-\*\/\.\(\)\^]+$', msg)
    if math_only:
        result = solve_math(msg)
        if result:
            return f"The answer is **{result}**."

    word_math = re.search(r'(\d+)\s*(plus|minus|times|multiplied by|divided by)\s*(\d+)', lower)
    if word_math:
        a, op, b = int(word_math.group(1)), word_math.group(2), int(word_math.group(3))
        results_map = {"plus": a+b, "minus": a-b, "times": a*b, "multiplied by": a*b, "divided by": round(a/b, 4) if b else "undefined"}
        return f"The answer is **{results_map.get(op, 'unknown')}**."

    math_q = re.search(r'(?:what(?:\'s| is)|calculate|solve|compute)\s+([\d\s\+\-\*\/\.\(\)\^]+)', lower)
    if math_q:
        result = solve_math(math_q.group(1))
        if result:
            return f"The answer is **{result}**."

    word_math = re.search(r'(\d+)\s*(plus|minus|times|multiplied by|divided by)\s*(\d+)', lower)
    if word_math:
        a, op, b = int(word_math.group(1)), word_math.group(2), int(word_math.group(3))
        results_map = {"plus": a+b, "minus": a-b, "times": a*b, "multiplied by": a*b, "divided by": round(a/b, 4) if b else "undefined"}
        return f"The answer is **{results_map.get(op, 'unknown')}**."

    if any(w in lower for w in ["hello", "hi ", "hi!", "hey", "good morning", "good afternoon", "good evening", "howdy"]) or lower in ["hi", "hey", "hello"]:
        return random.choice(GREETINGS).replace("!", f", {user_name}!", 1) if random.random() > 0.5 else random.choice(GREETINGS)

    if "how are you" in lower:
        return f"I'm doing well, thank you for asking! More importantly, how are *you* feeling today, {user_name}?"

    if any(w in lower for w in ["who are you", "what are you", "what can you do", "what do you do"]):
        return ABOUT_ME

    if any(w in lower for w in ["thank", "thanks", "appreciate"]):
        return f"You're welcome, {user_name}. I'm always here if you need to talk. 💛"

    if "your name" in lower:
        return "I'm Kansi AI — your mental health screening companion."

    if any(w in lower for w in ["joke", "funny", "make me laugh"]):
        jokes = [
            "Why did the scarecrow win an award? Because he was outstanding in his field! 😄",
            "What do you call a fake noodle? An impasta! 🍝",
            "Why don't scientists trust atoms? Because they make up everything! 🔬",
        ]
        return random.choice(jokes)

    if any(w in lower for w in ["weather", "temperature", "rain"]):
        return "I can't check live weather, but I hope it's pleasant where you are! Is there something else I can help with?"

    if any(w in lower for w in ["time", "date", "day is it"]):
        from datetime import datetime
        now = datetime.now()
        return f"It's currently {now.strftime('%A, %B %d, %Y at %I:%M %p')}."

    if any(w in lower for w in ["capital of", "president of", "population of"]):
        knowledge = {
            "united kingdom": "London", "uk": "London", "england": "London",
            "united states": "Washington, D.C.", "usa": "Washington, D.C.", "us": "Washington, D.C.",
            "france": "Paris", "germany": "Berlin", "japan": "Tokyo", "china": "Beijing",
            "nigeria": "Abuja", "south africa": "Pretoria", "india": "New Delhi",
            "canada": "Ottawa", "australia": "Canberra", "brazil": "Brasília",
        }
        for country, capital in knowledge.items():
            if country in lower:
                return f"The capital of {country.title()} is **{capital}**."
        return "That's a great question! I have limited general knowledge — I'm best at emotional support and basic queries."

    if any(w in lower for w in ["meaning of life", "why are we here", "purpose"]):
        return "That's one of humanity's deepest questions. While I can't answer it definitively, I believe every person brings something unique and valuable to the world — including you."

    if any(w in lower for w in ["sad", "upset", "down", "unhappy", "crying", "depressed", "miserable", "low", "broken"]):
        return random.choice(EMPATHY_SAD)

    if any(w in lower for w in ["anxious", "worried", "nervous", "scared", "panic", "stressed", "overwhelmed", "fear"]):
        return random.choice(EMPATHY_ANXIOUS)

    if any(w in lower for w in ["happy", "great", "good", "wonderful", "amazing", "fantastic", "excited", "joy"]):
        return random.choice(EMPATHY_HAPPY)

    if any(w in lower for w in ["angry", "furious", "mad", "frustrated", "rage", "annoyed", "irritated"]):
        return "It's completely okay to feel angry. Anger often signals that something important to you has been crossed. Would you like to talk about what's frustrating you?"

    if any(w in lower for w in ["lonely", "alone", "isolated", "no friends", "nobody cares"]):
        return f"Feeling lonely can be incredibly painful, {user_name}. But you're reaching out right now, and that takes courage. You matter, and your feelings matter. Would you like to talk about it?"

    if any(w in lower for w in ["sleep", "insomnia", "can't sleep", "nightmares"]):
        return "Sleep difficulties can really affect how we feel. Have you tried a calming routine before bed? If sleep problems persist, it might help to speak with a healthcare professional."

    if any(w in lower for w in ["eat", "appetite", "food", "hungry", "not eating"]):
        return "Changes in appetite can be connected to how we're feeling emotionally. It's worth paying attention to. If this has been going on for a while, a professional could offer helpful guidance."

    if any(w in lower for w in ["help me", "i need help", "support"]):
        return f"I'm here for you, {user_name}. You can share whatever is on your mind, and I'll do my best to support you. For professional help, please reach out to a therapist or counsellor."

    if any(w in lower for w in ["breathe", "breathing", "calm down", "relax"]):
        return "Let's try a breathing exercise: breathe in slowly for 4 counts... hold for 4 counts... and breathe out for 6 counts. Repeat this a few times. How do you feel?"

    if "?" in msg:
        return f"That's a thoughtful question. I'll do my best: while I have limited general knowledge, I'm always here to listen and support you emotionally. Could you tell me more about what you'd like to know?"

    return random.choice(FALLBACK)

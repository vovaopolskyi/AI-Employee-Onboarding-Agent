
import json
import random
from pathlib import Path

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.json"


def load_questions() -> list[dict]:
    with QUESTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_question(topic: str, difficulty: str = "any") -> dict:
    questions = load_questions()

    matches = [
        question
        for question in questions
        if question["topic"].lower() == topic.strip().lower()
        and (
            difficulty.lower() == "any"
            or question["difficulty"].lower() == difficulty.lower()
        )
    ]

    if not matches:
        return {"error": "No matching questions found"}

    question = random.choice(matches)

    return {
        "id": question["id"],
        "topic": question["topic"],
        "difficulty": question["difficulty"],
        "question": question["question"],
        "options": question["options"],
    }


def check_answer(question_id: str, answer: str) -> dict:
    for question in load_questions():
        if question["id"] == question_id:
            selected = answer.strip().upper()

            return {
                "correct": selected == question["answer"],
                "correct_answer": question["answer"],
                "explanation": question["explanation"],
            }

    return {"error": "Unknown question ID"}

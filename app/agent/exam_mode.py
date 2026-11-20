
import random
import secrets
from threading import Lock

from strands import tool
from question_bank import load_questions
from progress import save_exam_result

# Temporary in-memory exam sessions.
# Sessions disappear when the Python process restarts.
EXAMS = {}
EXAMS_LOCK = Lock()


def public_question(question: dict, number: int, total: int) -> dict:
    return {
        "number": number,
        "total": total,
        "id": question["id"],
        "topic": question["topic"],
        "question": question["question"],
        "options": question["options"],
    }


def start_exam(topic: str = "all", count: int = 10) -> dict:
    if not isinstance(count, int) or isinstance(count, bool):
        return {"error": "Count must be an integer"}

    if count < 1 or count > 20:
        return {"error": "Exam length must be between 1 and 20"}

    questions = load_questions()

    if topic.strip().lower() != "all":
        questions = [
            q for q in questions
            if q["topic"].lower() == topic.strip().lower()
        ]

    if len(questions) < count:
        return {
            "error": "Not enough questions for this exam",
            "available": len(questions),
        }

    selected = random.sample(questions, count)
    session_id = secrets.token_urlsafe(24)

    with EXAMS_LOCK:
        EXAMS[session_id] = {
            "questions": selected,
            "answers": {},
            "finished": False,
        }

    return {
        "session_id": session_id,
        "status": "in_progress",
        "question": public_question(selected[0], 1, count),
    }


def submit_answer(
    session_id: str,
    question_id: str,
    answer: str,
) -> dict:
    selected_answer = answer.strip().upper()

    if selected_answer not in ("A", "B", "C", "D"):
        return {"error": "Answer must be A, B, C, or D"}

    with EXAMS_LOCK:
        exam = EXAMS.get(session_id)

        if exam is None:
            return {"error": "Exam session not found"}

        if exam["finished"]:
            return {"error": "Exam already finished"}

        questions = exam["questions"]
        answer_index = len(exam["answers"])

        if answer_index >= len(questions):
            return {"error": "All questions already answered"}

        expected_question = questions[answer_index]

        if expected_question["id"] != question_id:
            return {"error": "Answer the current question first"}

        exam["answers"][question_id] = selected_answer
        next_index = answer_index + 1

        if next_index == len(questions):
            return {
                "status": "ready_to_finish",
                "answered": next_index,
                "total": len(questions),
                "message": "All answers saved. Finish the exam.",
            }

        next_question = public_question(
            questions[next_index],
            next_index + 1,
            len(questions),
        )

        return {
            "status": "in_progress",
            "answered": next_index,
            "question": next_question,
        }


def finish_exam(session_id: str) -> dict:
    with EXAMS_LOCK:
        exam = EXAMS.get(session_id)

        if exam is None:
            return {"error": "Exam session not found"}

        if exam["finished"]:
            return {"error": "Exam already finished"}

        questions = exam["questions"]
        answers = exam["answers"]

        if len(answers) != len(questions):
            return {
                "error": "Answer all questions before finishing",
                "answered": len(answers),
                "total": len(questions),
            }

        results = []

        for question in questions:
            selected = answers[question["id"]]
            correct = selected == question["answer"]

            results.append({
                "question_id": question["id"],
                "topic": question["topic"],
                "selected_answer": selected,
                "correct_answer": question["answer"],
                "correct": correct,
                "explanation": question["explanation"],
            })

        score = sum(item["correct"] for item in results)
        total = len(questions)
        percentage = round(score / total * 100, 1)

        final_result = {
            "status": "completed",
            "score": score,
            "total": total,
            "percentage": percentage,
            "passed": percentage >= 70,
            "pass_threshold": 70,
            "results": results,
        }

        save_exam_result(session_id, final_result)

        exam["finished"] = True

        return final_result


@tool
def start_practice_exam(
    topic: str = "all",
    count: int = 10,
) -> dict:
    """Start an AWS practice exam without revealing answers.

    Args:
        topic: AWS topic or all for mixed topics.
        count: Number of questions, between 1 and 20.
    """
    return start_exam(topic, count)


@tool
def submit_exam_answer(
    session_id: str,
    question_id: str,
    answer: str,
) -> dict:
    """Submit one exam answer and receive the next question.

    Args:
        session_id: Session ID returned when starting the exam.
        question_id: ID of the current question.
        answer: Chosen option A, B, C, or D.
    """
    return submit_answer(session_id, question_id, answer)


@tool
def finish_practice_exam(session_id: str) -> dict:
    """Finish a completed exam and return its score and explanations.

    Args:
        session_id: Session ID returned when starting the exam.
    """
    return finish_exam(session_id)

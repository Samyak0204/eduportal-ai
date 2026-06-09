import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

# Reconfigure stdout to support unicode prints on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from gemini_eval import evaluate_answer
from db import get_db, seed_default_users

load_dotenv()

# Test 1: DB Seeding and Connection Check
print("=== Integration Test 1: DB Connection and Seeding ===")
try:
    db = get_db()
    db.command("ping")
    print("[OK] Connected to MongoDB database successfully.")
    
    # Try seeding
    seed_default_users()
    print("[OK] Seeding default users executed successfully.")
except Exception as e:
    print(f"[FAIL] MongoDB test failed: {e}")

# Test 2: Evaluate MCQ
print("\n=== Integration Test 2: Evaluate MCQ Answer ===")
try:
    question_text = "What is the capital of France?"
    options = {"A": "Berlin", "B": "Madrid", "C": "Paris", "D": "Rome"}
    correct_option = "C"
    
    student_answer = "C" # Student answered Paris
    print(f"Question: {question_text}")
    print(f"Student Answer: {student_answer}")
    
    eval_result = evaluate_answer(
        question_text=question_text,
        question_type="Multiple Choice",
        answer_text=student_answer,
        options=options,
        correct_option=correct_option
    )
    print("\nGemini MCQ Evaluation Result:")
    print(eval_result)
    
    if "Verdict" in eval_result and "Correct" in eval_result:
         print("\n[OK] MCQ evaluation successfully identified the correct answer!")
    else:
         print("\n[WARNING] Evaluation completed but check verdict structure.")
except Exception as e:
    print(f"[FAIL] MCQ evaluation failed: {e}")

# Test 3: Evaluate Math Question with Ideal Answer
print("\n=== Integration Test 3: Evaluate Math Question with Ideal Answer ===")
try:
    question_text = "Solve for x: 2x + 5 = 15"
    ideal_answer = "Subtract 5 from both sides: 2x = 10. Divide by 2: x = 5."
    student_answer = "First subtract 5 to get 2x = 10, then divide by 2, so x = 5."
    
    print(f"Question: {question_text}")
    print(f"Ideal Answer: {ideal_answer}")
    print(f"Student Answer: {student_answer}")
    
    eval_result = evaluate_answer(
        question_text=question_text,
        question_type="Math / Equations",
        answer_text=student_answer,
        ideal_answer=ideal_answer
    )
    print("\nGemini Math Evaluation Result:")
    print(eval_result)
    
    if "Correct" in eval_result:
         print("\n[OK] Math evaluation completed successfully!")
    else:
         print("\n[WARNING] Math evaluation ran, check output.")
except Exception as e:
    print(f"[FAIL] Math evaluation failed: {e}")

# Test 4: Evaluate Code Question
print("\n=== Integration Test 4: Evaluate Code Question ===")
try:
    question_text = "Write a python function to return the square of a number."
    ideal_answer = "def square(x):\n    return x * x"
    student_answer = "```python\ndef square(n):\n    return n ** 2\n```"
    
    print(f"Question: {question_text}")
    print(f"Ideal Answer: {ideal_answer}")
    print(f"Student Answer: {student_answer}")
    
    eval_result = evaluate_answer(
        question_text=question_text,
        question_type="Code Problem",
        answer_text=student_answer,
        ideal_answer=ideal_answer
    )
    print("\nGemini Code Evaluation Result:")
    print(eval_result)
    
    if "Correct" in eval_result:
         print("\n[OK] Code evaluation completed successfully!")
    else:
         print("\n[WARNING] Code evaluation ran, check output.")
except Exception as e:
    print(f"[FAIL] Code evaluation failed: {e}")

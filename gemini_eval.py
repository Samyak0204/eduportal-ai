import os
import base64
import time
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

MODEL = "gemini-2.5-flash"


def _generate_content_with_retry(model, contents, max_retries=3, backoff_factor=2):
    delay = 2.0
    for attempt in range(max_retries):
        try:
            return model.generate_content(contents)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota exceeded" in err_str or "ResourceExhausted" in err_str or "Rate limit" in err_str:
                if attempt < max_retries - 1:
                    # Try to parse the exact retry delay requested by Gemini
                    match = re.search(r"Please retry in (\d+\.?\d*)s", err_str)
                    if match:
                        sleep_time = float(match.group(1)) + 1.5
                    else:
                        match_sec = re.search(r"seconds:\s*(\d+)", err_str)
                        if match_sec:
                            sleep_time = float(match_sec.group(1)) + 1.5
                        else:
                            sleep_time = delay
                            delay *= backoff_factor
                    print(f"[Gemini] Quota limit hit. Sleeping for {sleep_time:.2f} seconds before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
            raise e


def _build_prompt(question_text: str, question_type: str, answer_text: str = None,
                  options: dict = None, correct_option: str = None, ideal_answer: str = None,
                  explanation: str = None, is_attachment: bool = False) -> str:
    details = []
    if options:
        opts_str = "\n".join([f"- {k}: {v}" for k, v in options.items()])
        details.append(f"OPTIONS:\n{opts_str}")
    if correct_option:
        details.append(f"CORRECT OPTION: {correct_option}")
    if ideal_answer:
        details.append(f"IDEAL CORRECT ANSWER/RUBRIC:\n{ideal_answer}")
    if explanation:
        details.append(f"EXPLANATION/RATIONALE WHY IT IS CORRECT:\n{explanation}")
    
    details_block = "\n\n".join(details)
    if details_block:
        details_block = "\n" + details_block

    student_ans_display = answer_text if (answer_text and answer_text.strip()) else ("(provided as image — see attached)" if is_attachment else "(No answer provided)")

    return f"""
You are an expert academic evaluator. A student has answered the following question.

QUESTION TYPE: {question_type}
QUESTION: {question_text}{details_block}

STUDENT'S ANSWER: {student_ans_display}

Please evaluate the student's answer and respond in the following structured format:

## ✅ Verdict
State clearly: Correct / Partially Correct / Incorrect

## 📊 Score
Give a score out of 10 with a brief justification.

## 🔍 Analysis
Provide a detailed analysis of the student's answer — what they got right, what they missed, any misconceptions.

## 💡 Correct Answer & Explanation
Provide the complete, ideal correct answer and explain clearly WHY it is correct. Use the IDEAL CORRECT ANSWER/RUBRIC and EXPLANATION/RATIONALE if provided as your primary reference.

## 📝 Suggestions
Give 2-3 specific tips for the student to improve.
"""


def evaluate_text_answer(question_text: str, question_type: str, answer_text: str,
                         options: dict = None, correct_option: str = None, ideal_answer: str = None,
                         explanation: str = None) -> str:
    try:
        model = genai.GenerativeModel(MODEL)
        prompt = _build_prompt(question_text, question_type, answer_text, options, correct_option, ideal_answer, explanation, is_attachment=False)
        response = _generate_content_with_retry(model, prompt)
        return response.text
    except Exception as e:
        return f"❌ Gemini Error: {str(e)}"


def evaluate_image_answer(question_text: str, question_type: str, image_bytes: bytes, mime_type: str = "image/png",
                          options: dict = None, correct_option: str = None, ideal_answer: str = None,
                          explanation: str = None) -> str:
    try:
        model = genai.GenerativeModel(MODEL)
        prompt = _build_prompt(question_text, question_type, answer_text=None, options=options, correct_option=correct_option, ideal_answer=ideal_answer, explanation=explanation, is_attachment=True)
        image_part = {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}
        response = _generate_content_with_retry(model, [prompt, image_part])
        return response.text
    except Exception as e:
        return f"❌ Gemini Error: {str(e)}"


def evaluate_audio_answer(question_text: str, question_type: str, audio_bytes: bytes, mime_type: str = "audio/wav",
                          options: dict = None, correct_option: str = None, ideal_answer: str = None,
                          explanation: str = None) -> str:
    try:
        model = genai.GenerativeModel(MODEL)
        details = []
        if options:
            opts_str = "\n".join([f"- {k}: {v}" for k, v in options.items()])
            details.append(f"OPTIONS:\n{opts_str}")
        if correct_option:
            details.append(f"CORRECT OPTION: {correct_option}")
        if ideal_answer:
            details.append(f"IDEAL CORRECT ANSWER/RUBRIC:\n{ideal_answer}")
        if explanation:
            details.append(f"EXPLANATION/RATIONALE WHY IT IS CORRECT:\n{explanation}")
        
        details_block = "\n\n".join(details)
        if details_block:
            details_block = "\n" + details_block

        prompt = f"""
You are an expert academic evaluator. A student has answered the following question via audio recording.

QUESTION TYPE: {question_type}
QUESTION: {question_text}{details_block}

First, transcribe the student's audio answer, then evaluate it using this format:

## 🎙️ Transcription
[Transcribe the audio answer here]

## ✅ Verdict
State clearly: Correct / Partially Correct / Incorrect

## 📊 Score
Give a score out of 10 with a brief justification.

## 🔍 Analysis
Provide a detailed analysis of the student's answer — what they got right, what they missed, any misconceptions.

## 💡 Correct Answer & Explanation
Provide the complete, ideal correct answer and explain clearly WHY it is correct. Use the IDEAL CORRECT ANSWER/RUBRIC and EXPLANATION/RATIONALE if provided as your primary reference.

## 📝 Suggestions
Give 2-3 specific tips for the student to improve.
"""
        audio_part = {"mime_type": mime_type, "data": base64.b64encode(audio_bytes).decode()}
        response = _generate_content_with_retry(model, [prompt, audio_part])
        return response.text
    except Exception as e:
        return f"❌ Gemini Error: {str(e)}"


def evaluate_answer(question_text: str, question_type: str,
                    answer_text: str = None,
                    image_bytes: bytes = None, image_mime: str = "image/png",
                    audio_bytes: bytes = None, audio_mime: str = "audio/wav",
                    options: dict = None, correct_option: str = None, ideal_answer: str = None,
                    explanation: str = None) -> str:
    if image_bytes:
        return evaluate_image_answer(question_text, question_type, image_bytes, image_mime, options, correct_option, ideal_answer, explanation)
    elif audio_bytes:
        return evaluate_audio_answer(question_text, question_type, audio_bytes, audio_mime, options, correct_option, ideal_answer, explanation)
    else:
        return evaluate_text_answer(question_text, question_type, answer_text or "", options, correct_option, ideal_answer, explanation)


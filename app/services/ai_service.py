from typing import List, Dict
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings
from app.models.feedback import (
    FeedbackAnalysis,
    SentimentDistribution,
)


class AIService:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            temperature=0.1,
            max_tokens=6000,
        )
        self.parser = PydanticOutputParser(pydantic_object=FeedbackAnalysis)
        self.analysis_prompt = ChatPromptTemplate.from_template(
            """You are a product feedback analyst. Analyze the following customer feedback and return a complete JSON response.

FEEDBACKS TO ANALYZE ({feedback_count} total):
{feedbacks}

YOUR MISSION:
Extract sentiment, identify themes, and provide actionable recommendations.
Write a COMPLETE, DETAILED analytical report in 'chat_response'. Do NOT cut it short.

RESPONSE FORMAT RULES for 'chat_response':
1. Use markdown headers (###, **) and bullet points.
2. Use emojis (✅, 🟠, 🟢, 🔴, ❌, ⚠️) for visual clarity.
3. MENTION SPECIFIC QUOTES from actual feedback. Include at least 3-5 real examples.
4. NO preamble. Start directly with the analysis summary line.
5. WRITE OUT ALL SECTIONS FULLY — do not truncate or abbreviate.

TEMPLATE (write every section completely):
"Analyzed {feedback_count} feedback/s. [Sentiment] sentiment ([X]% satisfaction).

**Key Insights:**
- [Emoji] **Strengths:** [Specific positive attributes found — quote examples]
- [Emoji] **Weaknesses:** [Critical issues or complaints — quote examples]

**Detailed Analysis:**
[For each major theme, one row per theme]:
✅ [Theme]: [Summary] - "[Specific quote from feedback]"
❌ [Theme]: [Summary] - "[Specific quote from feedback]"

**Priority Actions:**
🔴 **CRITICAL:** [Title]
   Issue: [What happened in feedback]
   Impact: [How it affects users]
   Action: [Direct instruction]

🟠 **HIGH:** [Title]
   Issue: [Details]
   Impact: [Details]
   Action: [Details]

🟢 **MAINTAIN:** [Positive area to keep stable]

**Expected Impact:**
[Professional 2-3 sentence summary of how these actions will improve the product]"

RULES:
- If the feedback mentions "clean", "easy", "smooth", "fast", or "helpful", the sentiment MUST be "positive".
- Ensure 'sentiment_distribution' counts sum to exactly {feedback_count}.
- Return ONLY valid JSON matching the schema below.
- The 'chat_response' field MUST be complete — never end mid-sentence.

{format_instructions}"""
        )

        self.question_prompt = ChatPromptTemplate.from_template(
            """You are a senior product analyst answering a PRODUCT MANAGER'S question about customer feedback data.
PRODUCT MANAGER'S QUESTION:
{question}

AVAILABLE ANALYTICS:
- Total analyzed: {total_feedbacks}
- Sentiment: {sentiment_dist}
- Top Themes: {top_themes}
- Recommendations: {features}

RAW FEEDBACK SAMPLES:
{samples}

PREVIOUS CONVERSATION:
{history}

YOUR TASK:
Provide a comprehensive, professional, and detailed answer. 

CRITICAL RULES:
1. Use bullet points and separate lines for every major point. 
2. BE SPECIFIC AND ANALYTICAL. Avoid generic advice like "maintain quality". Instead, pin-point specific features, mentions, or trends from the data.
3. INDUSTRY ACCURACY: If the PM asks about a specific category (e.g., SaaS, Software), filter the RAW FEEDBACK SAMPLES for relevant keywords (UI, speed, features, bugs). 
4. DO NOT mix unrelated categories. If asking about SaaS, do not mention "food quality" or "packaging" unless they are specifically part of the SaaS data.
5. Provide at least 3-5 specific quotes or paraphrased examples from the samples.
6. FOCUS ON ACTION: What specific technical or operational change is needed based on the patterns?

Return a clear, structured, and long-form response."""
        )

        self.intent_prompt = ChatPromptTemplate.from_template(
            "You are an intent classification engine for a product feedback platform. "
            "Your job is to strictly differentiate between raw product feedback and a user chatting/asking questions.\n\n"
            "Analyze the following user input and determine whether it is:\n"
            "1. 'FEEDBACK': The user is explicitly writing a new review, feature request, or bug report about a software product (e.g., 'The app crashes on login', 'I hate the new UI', 'Add dark mode please').\n"
            "2. 'CONVERSATION': The user is saying hello, asking a question (how, what, why, can you, do you), requesting a summary, discussing existing data, or giving a command (e.g., 'Summarize the file', 'What are the main complaints?').\n\n"
            "CRITICAL RULES:\n"
            "- If the input is a question (ends with '?' or starts with a question word), it is ALWAYS 'CONVERSATION'.\n"
            "- If the input is a command to the AI (e.g., 'tell me', 'analyze', 'summarize', 'find'), it is ALWAYS 'CONVERSATION'.\n"
            "- If the input is a greeting ('hi', 'hello', 'hey'), it is ALWAYS 'CONVERSATION'.\n\n"
            "User Input: '{message}'\n\n"
            "Respond strictly with exactly one word: FEEDBACK or CONVERSATION"
        )

    def classify_intent(self, message: str) -> str:
        chain = self.intent_prompt | self.llm
        try:
            result = chain.invoke({"message": message})
            intent = result.content.strip().upper()
            if "FEEDBACK" in intent:
                return "FEEDBACK"
            return "CONVERSATION"
        except Exception as e:
            print(f"Intent Classification Error: {str(e)}")
            return "CONVERSATION"

    def analyze_feedback(
        self, reviews: List[str], history: List[Dict[str, str]] = []
    ) -> FeedbackAnalysis:
        feedback_count = len(reviews)

        MAX_SAMPLES = 80
        if feedback_count > MAX_SAMPLES:
            import random

            random.seed(42)

            neg_keywords = [
                "bad",
                "terrible",
                "slow",
                "worst",
                "hate",
                "poor",
                "broken",
                "crash",
                "issue",
                "problem",
                "unusable",
                "awful",
            ]
            pos_keywords = [
                "good",
                "great",
                "excellent",
                "love",
                "amazing",
                "best",
                "perfect",
                "fast",
                "smooth",
                "easy",
            ]

            negatives = [
                r for r in reviews if any(w in r.lower() for w in neg_keywords)
            ]
            positives = [
                r for r in reviews if any(w in r.lower() for w in pos_keywords)
            ]
            neutrals = [r for r in reviews if r not in negatives and r not in positives]

            n_neg = min(len(negatives), 30)
            n_pos = min(len(positives), 30)
            n_neu = max(0, MAX_SAMPLES - n_neg - n_pos)
            n_neu = min(n_neu, len(neutrals))

            sampled = (
                random.sample(negatives, n_neg)
                + random.sample(positives, n_pos)
                + random.sample(neutrals, n_neu)
            )
            random.shuffle(sampled)
            sample_note = f"(Showing {len(sampled)} representative samples out of {feedback_count} total)"
        else:
            sampled = reviews
            sample_note = ""

        if len(sampled) == 1:
            formatted_feedbacks = f'Single feedback:\n"{sampled[0]}"'
        else:
            formatted_feedbacks = f"Customer feedbacks {sample_note}:\n"
            for i, review in enumerate(sampled, 1):
                clean_review = self._clean_feedback(review)
                if clean_review:
                    formatted_feedbacks += f'{i}. "{clean_review}"\n'

        chain = self.analysis_prompt | self.llm | self.parser
        try:
            result = chain.invoke(
                {
                    "feedback_count": feedback_count,
                    "feedbacks": formatted_feedbacks,
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )
            result.total_feedbacks_analyzed = feedback_count
            result.is_question_response = False
            result = self._validate_and_enhance(result, feedback_count)
            return result
        except Exception as e:
            print(f"AI Analysis Error: {str(e)}")
            return self._create_fallback_analysis(reviews)

    def answer_question(
        self,
        question: str,
        analysis_data: FeedbackAnalysis,
        history: List[Dict[str, str]] = [],
        raw_feedbacks: List[str] = [],
    ) -> str:
        sentiment_dist = f"{analysis_data.sentiment_distribution.positive_percentage:.0f}% positive, {analysis_data.sentiment_distribution.negative_percentage:.0f}% negative"
        top_themes = (
            ", ".join([f"{t.theme} ({t.count}x)" for t in analysis_data.themes[:5]])
            if analysis_data.themes
            else "No themes detected"
        )
        features = (
            ", ".join(
                [
                    f"{f.feature} ({f.priority} priority)"
                    for f in analysis_data.feature_suggestions[:3]
                ]
            )
            if analysis_data.feature_suggestions
            else "No suggestions yet"
        )

        samples = ""
        question_lower = question.lower()

        context_keywords = [
            "bad",
            "negative",
            "complaint",
            "issue",
            "problem",
            "example",
            "saas",
            "category",
            "software",
            "ui",
            "performance",
            "praise",
            "good",
        ]

        if (
            any(kw in question_lower for kw in context_keywords)
            or len(raw_feedbacks) < 20
        ):
            relevant_samples = []

            if any(
                kw in question_lower
                for kw in ["bad", "complaint", "issue", "negative", "problem"]
            ):
                neg = [
                    r
                    for r in raw_feedbacks
                    if any(
                        w in str(r).lower()
                        for w in [
                            "bad",
                            "worst",
                            "hate",
                            "terrible",
                            "disappointed",
                            "poor",
                            "slow",
                            "broken",
                            "issue",
                        ]
                    )
                ]
                relevant_samples.extend(neg[:15])

            if "saas" in question_lower or "software" in question_lower:
                software = [
                    r
                    for r in raw_feedbacks
                    if any(
                        w in str(r).lower()
                        for w in [
                            "software",
                            "ui",
                            "ux",
                            "app",
                            "performance",
                            "slow",
                            "interface",
                            "bug",
                            "crash",
                        ]
                    )
                ]
                relevant_samples.extend(software[:15])

            if len(relevant_samples) < 10:
                relevant_samples.extend(raw_feedbacks[:20])

            seen = set()
            unique_samples = []
            for s in relevant_samples:
                s_str = str(s).strip()
                if s_str not in seen and len(s_str) > 10:
                    unique_samples.append(s_str)
                    seen.add(s_str)

            if unique_samples:
                samples = "SELECTED RAW FEEDBACK SAMPLES FOR CONTEXT:\n" + "\n".join(
                    [f"- {s[:300]}" for s in unique_samples[:30]]
                )

        formatted_history = (
            "\n".join(
                [
                    f"{'User' if msg['role'] == 'user' else 'Analyst'}: {msg['content']}"
                    for msg in history[-5:]
                ]
            )
            if history
            else "No previous conversation"
        )

        chain = self.question_prompt | self.llm
        try:
            result = chain.invoke(
                {
                    "question": question,
                    "total_feedbacks": analysis_data.total_feedbacks_analyzed,
                    "sentiment_dist": sentiment_dist,
                    "top_themes": top_themes,
                    "features": features,
                    "history": formatted_history,
                    "samples": samples,
                }
            )
            return result.content
        except Exception as e:
            print(f"Question answering error: {str(e)}")
            return "I encountered an error answering your question. Please try rephrasing it."

    def _clean_feedback(self, feedback: str) -> str:
        if not feedback:
            return ""
        return feedback.strip().strip('"').strip("'")

    def _validate_and_enhance(
        self, result: FeedbackAnalysis, expected_count: int
    ) -> FeedbackAnalysis:
        dist = result.sentiment_distribution
        dist_total = dist.positive + dist.neutral + dist.negative + dist.mixed

        if expected_count == 1:
            result.total_feedbacks_analyzed = 1
            current_total = 1
        elif dist_total > expected_count:
            result.total_feedbacks_analyzed = dist_total
            current_total = dist_total
        else:
            result.total_feedbacks_analyzed = expected_count
            current_total = expected_count

        import re

        result.chat_response = re.sub(
            r"Analyzed \d+ feedback/s?",
            f"Analyzed {current_total} feedback{'s' if current_total != 1 else ''}",
            result.chat_response,
        )

        if current_total == 1:
            sentiment = result.overall_sentiment.lower()
            dist.positive = 1 if sentiment == "positive" else 0
            dist.negative = 1 if sentiment == "negative" else 0
            dist.mixed = 1 if sentiment == "mixed" else 0
            dist.neutral = (
                1
                if sentiment == "neutral"
                and not (
                    getattr(dist, "positive", 0)
                    or getattr(dist, "negative", 0)
                    or getattr(dist, "mixed", 0)
                )
                else 0
            )

        result.chat_response = result.chat_response.replace(
            "1 feedback/s", "1 feedback"
        ).replace("1 feedbacks", "1 feedback")

        for theme in result.themes:
            s = theme.sentiment.lower()
            if s == "positive":
                theme.satisfaction = 100
            elif s == "negative":
                theme.satisfaction = 0
            elif s == "mixed":
                theme.satisfaction = 50
            else:
                theme.satisfaction = 50
        return result

    def _create_fallback_analysis(self, reviews: List[str]) -> FeedbackAnalysis:
        feedback_count = len(reviews)
        text_combined = " ".join(reviews).lower()
        positive_words = [
            "good",
            "great",
            "excellent",
            "love",
            "amazing",
            "best",
            "perfect",
        ]
        negative_words = [
            "bad",
            "terrible",
            "slow",
            "worst",
            "hate",
            "poor",
            "broken",
            "crash",
        ]

        pos_count = sum(1 for word in positive_words if word in text_combined)
        neg_count = sum(1 for word in negative_words if word in text_combined)

        if pos_count > neg_count:
            sentiment = "positive"
            score = 0.75
            pos, neu, neg = feedback_count, 0, 0
        elif neg_count > pos_count:
            sentiment = "negative"
            score = 0.25
            pos, neu, neg = 0, 0, feedback_count
        else:
            sentiment = "neutral"
            score = 0.5
            pos, neu, neg = 0, feedback_count, 0

        return FeedbackAnalysis(
            total_feedbacks_analyzed=feedback_count,
            overall_sentiment=sentiment,
            satisfaction_index=score,
            sentiment_distribution=SentimentDistribution(
                positive=pos, neutral=neu, negative=neg, mixed=0
            ),
            total_themes_detected=0,
            themes=[],
            key_features_count=0,
            feature_suggestions=[],
            chat_response=f"""Analyzed {feedback_count} feedback/s. {sentiment.capitalize()} sentiment ({int(score * 100)}% satisfaction).

**Key Insights:**
- ⚠️ **Strengths/Weaknesses:** Analysis interrupted or low data quality.

**Detailed Analysis:**
⚡ System performing fallback classification.
🔴 Unable to extract detailed themes at this time.

**Priority Actions:**
1. 🔴 **CRITICAL:** Provide more detailed feedback
   - Issue: Low data density
   - Impact: Prevents deep neural analysis
   - Action: Submit multiple specific feedbacks

**Expected Impact:** 
Improving feedback detail will enable full keyword extraction and theme analysis.""",
            is_question_response=False,
        )

    def is_question(self, message: str) -> bool:
        msg = message.lower().strip()

        if msg.endswith("?"):
            return True

        starters = [
            "what",
            "how",
            "why",
            "when",
            "which",
            "who",
            "where",
            "tell me",
            "show me",
            "give me",
            "list",
            "find",
            "can you",
            "could you",
            "should i",
            "analyze reviews",
            "summarize data",
        ]
        if any(msg.startswith(s) for s in starters):
            return True

        query_keywords = [
            "sentiment breakdown",
            "theme analysis",
            "feature suggestions",
            "top complaints",
            "overall status",
            "satisfaction score",
        ]
        if any(kw in msg for kw in query_keywords) and len(msg.split()) < 10:
            return True

        command_verbs = ["analyze", "summarize", "list", "show", "tell", "find"]
        if any(msg.startswith(v) for v in command_verbs) and len(msg.split()) < 8:
            return True

        return False


ai_service = AIService()

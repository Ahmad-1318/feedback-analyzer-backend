from typing import List, Dict, Optional, Any
import csv
import io
from app.agents.feedback_agent import FeedbackAgent
from app.repositories.feedback_repository import FeedbackRepository
from app.models.feedback import FeedbackAnalysis
from app.services.ai_service import ai_service
from app.core.exceptions import ValidationError

class FeedbackService:
    def __init__(self, feedback_repo: FeedbackRepository):
        self.feedback_repo = feedback_repo
        self._agent_cache: Dict[str, FeedbackAgent] = {}

    def _get_agent(self, user_id: str) -> FeedbackAgent:
        if user_id not in self._agent_cache:
            self._agent_cache[user_id] = FeedbackAgent(user_id=user_id)
        return self._agent_cache[user_id]

    async def process_message(
        self, user_id: str, message: str, conversation_id: Optional[str] = None
    ) -> Dict:
        if not conversation_id:
            conversation = self.feedback_repo.create_conversation(
                user_id=user_id, title=message[:50]
            )
            conversation_id = str(conversation["_id"])

        self.feedback_repo.create_message(
            conversation_id=conversation_id, role="user", content=message
        )

        intent = ai_service.classify_intent(message)
        is_new_feedback = (intent == "FEEDBACK")

        if is_new_feedback:
            result = await self._handle_new_feedback(
                user_id=user_id, feedback_text=message, conversation_id=conversation_id
            )
        else:
            result = await self._handle_question_with_agent(
                user_id=user_id, question=message, conversation_id=conversation_id
            )

        # Save assistant response
        self.feedback_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result["response"],
            metadata=result.get("metadata", {}),
        )

        return result

    async def _handle_new_feedback(
        self, user_id: str, feedback_text: str, conversation_id: str
    ) -> Dict:
        feedbacks = self._parse_feedbacks(feedback_text)
        analysis = ai_service.analyze_feedback(reviews=feedbacks, history=[])

        for feedback in feedbacks:
            stored_sentiment = (
                analysis.overall_sentiment
                if len(feedbacks) == 1
                else self._quick_sentiment(feedback)
            )

            self.feedback_repo.create_feedback(
                user_id=user_id,
                conversation_id=conversation_id,
                content=feedback,
                sentiment=stored_sentiment,
                sentiment_score=analysis.satisfaction_index,
                themes=[t.theme for t in analysis.themes[:3]]
                if analysis.themes
                else [],
            )

        self.feedback_repo.save_analysis(
            user_id=user_id,
            analysis=analysis,
            feedback_count=len(feedbacks),
            conversation_id=conversation_id,
        )

        return {
            "conversation_id": conversation_id,
            "response": analysis.chat_response,
            "analysis": analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict(),
            "metadata": {
                "type": "new_feedback_analysis",
                "feedbacks_analyzed": len(feedbacks),
                "satisfaction": int(analysis.satisfaction_index * 100),
                "sentiment": analysis.overall_sentiment,
                "index": int(analysis.satisfaction_index * 100),
            },
            "is_question": False,
            "success": True,
        }

    async def _handle_question_with_agent(
        self, user_id: str, question: str, conversation_id: str
    ) -> Dict:
        agent = self._get_agent(user_id)
        agent.set_conversation_id(conversation_id)

        db_messages = self.feedback_repo.get_conversation_messages(
            conversation_id, limit=10
        )
        history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in db_messages
            if msg["content"] != question
        ]

        result = agent.chat(message=question, history=history)

        return {
            "conversation_id": conversation_id,
            "response": result["response"],
            "analysis": None,
            "metadata": {
                "type": "agent_query",
                "tools_used": result.get("tools_used", []),
            },
            "is_question": True,
            "success": result["success"],
        }

    def _parse_feedbacks(self, text: str) -> List[str]:
        if len(text.split()) < 50 and "\n" not in text:
            return [text.strip()]

        lines = text.split("\n")
        feedbacks = []
        for line in lines:
            clean = line.strip().strip('"').strip("'")
            if len(clean) > 10:
                feedbacks.append(clean)

        return feedbacks if feedbacks else [text.strip()]

    def _quick_sentiment(self, text: str) -> str:
        import re
        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        positive_words = {"good", "great", "excellent", "love", "amazing", "best", "smooth", "smoothly", "perfect", "fantastic", "outstanding", "wonderful", "brilliant", "fast", "quick", "easy", "helpful", "useful", "nice", "pleased", "happy", "satisfied", "beautiful", "clean", "intuitive", "reliable", "effective", "efficient", "improved", "better", "awesome", "like", "enjoy", "enjoyed", "enjoying", "superb", "neat", "clear", "stable", "works", "working", "joy", "delight", "delightful", "fluid"}
        negative_words = {"bad", "terrible", "slow", "worst", "hate", "poor", "broken", "crash", "crashes", "crashing", "crashed", "bug", "bugs", "error", "errors", "problem", "problems", "fail", "fails", "failing", "failed", "failure", "useless", "awful", "horrible", "frustrating", "frustration", "annoying", "difficult", "confusing", "delayed", "delay", "not", "never", "cant", "cannot", "doesn", "doesn't", "won't", "wont", "missing", "lost", "broken", "laggy", "lag", "freeze", "freezing", "frozen", "unusable", "disappointing", "disappointed", "complaint", "complain"}
        mixed_connectors = {"but", "however", "although", "though", "yet", "while", "except", "unfortunately", "despite"}

        pos = len(words & positive_words)
        neg = len(words & negative_words)
        has_connector = bool(words & mixed_connectors)

        if pos > 0 and neg > 0: return "mixed"
        if has_connector and (pos > 0 or neg > 0): return "mixed"
        if pos > 0: return "positive"
        if neg > 0: return "negative"
        return "neutral"

    async def process_csv_upload(
        self, user_id: str, feedbacks: List[str], filename: str, conversation_id: Optional[str] = None
    ) -> Dict:
        if not conversation_id:
            conversation = self.feedback_repo.create_conversation(
                user_id=user_id, title=f"Dataset: {filename}"
            )
            conversation_id = str(conversation["_id"])

        feedback_docs = []
        for text in feedbacks:
            cleaned = text.strip()
            if cleaned:
                feedback_docs.append(
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "content": cleaned,
                        "sentiment": self._quick_sentiment(cleaned),
                        "sentiment_score": 0.5,
                        "themes": [],
                    }
                )

        if feedback_docs:
            self.feedback_repo.bulk_create_feedbacks(feedback_docs)

        analysis = ai_service.analyze_feedback(reviews=feedbacks, history=[])

        self.feedback_repo.save_analysis(
            user_id=user_id, analysis=analysis, feedback_count=len(feedbacks), conversation_id=conversation_id
        )

        self.feedback_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=analysis.chat_response,
            metadata={
                "type": "csv_analysis",
                "filename": filename,
                "feedbacks_analyzed": len(feedbacks),
                "sentiment": analysis.overall_sentiment,
                "index": int(analysis.satisfaction_index * 100),
            },
        )

        return {
            "conversation_id": conversation_id,
            "response": analysis.chat_response,
            "analysis": analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict(),
            "metadata": {
                "type": "new_feedback_batch",
                "filename": filename,
                "feedbacks_analyzed": len(feedbacks),
                "sentiment": analysis.overall_sentiment,
                "index": int(analysis.satisfaction_index * 100),
            },
            "is_question": False,
            "success": True,
        }

    async def process_csv_content(
        self, user_id: str, content: bytes, filename: str, conversation_id: Optional[str] = None
    ) -> Dict:
        try:
            decoded = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
            feedback_columns = [
                "review", "feedback", "text", "comment", "description", "content", "message"
            ]
            reviews = []
            for row in reader:
                for col in feedback_columns:
                    for key in row.keys():
                        if col.lower() in key.lower():
                            text = str(row[key]).strip()
                            if text and len(text) > 10:
                                reviews.append(text)
                            break
            if not reviews:
                reader = csv.DictReader(io.StringIO(decoded))
                for row in reader:
                    for value in row.values():
                        if isinstance(value, str) and len(value) > 20:
                            reviews.append(value.strip())
                            break
            if not reviews:
                raise ValidationError("No valid feedback found in CSV. Ensure it has a column like 'review', 'feedback', or 'text'.")

            return await self.process_csv_upload(
                user_id=user_id, feedbacks=reviews, filename=filename, conversation_id=conversation_id
            )
        except UnicodeDecodeError:
            raise ValidationError("Invalid file encoding. Please use UTF-8.")
        except csv.Error as e:
            raise ValidationError(f"CSV parsing error: {str(e)}")

    def get_quick_sentiment(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValidationError("Text cannot be empty")
        sentiment = self._quick_sentiment(text)
        confidence = 0.8 if sentiment != "neutral" else 0.5
        return {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "sentiment": sentiment,
            "confidence": confidence,
        }

    def analyze_reviews(
        self, reviews: List[str], history: List[Dict[str, str]] = None, user_id: str = None
    ) -> FeedbackAnalysis:
        analysis = ai_service.analyze_feedback(reviews=reviews, history=history or [])
        if user_id:
            self.feedback_repo.save_analysis(
                user_id=user_id, analysis=analysis, feedback_count=len(reviews)
            )
            for review in reviews:
                self.feedback_repo.create_feedback(
                    user_id=user_id,
                    content=review,
                    sentiment=analysis.overall_sentiment,
                    sentiment_score=analysis.satisfaction_index,
                    themes=[t.theme for t in analysis.themes],
                )
        return analysis

    def get_user_stats(self, user_id: str) -> Dict:
        return {
            "sentiment_distribution": self.feedback_repo.get_sentiment_stats(user_id),
            "top_themes": self.feedback_repo.get_theme_stats(user_id),
            "total_feedbacks": self.feedback_repo.get_feedback_count(user_id),
            "average_satisfaction": self.feedback_repo.get_average_satisfaction(user_id),
        }

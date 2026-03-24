from typing import List, Optional, Dict, Any
from datetime import datetime
from pymongo.database import Database
from bson import ObjectId
from app.models.feedback import FeedbackAnalysis


class FeedbackRepository:
    def __init__(self, db: Database):
        self.db = db
        self.feedback_collection = db["feedbacks"]
        self.analysis_collection = db["analyses"]
        self.conversation_collection = db["conversations"]
        self.message_collection = db["messages"]

    def create_feedback(
        self,
        user_id: str,
        content: str,
        sentiment: str = "neutral",
        sentiment_score: float = 0.5,
        themes: List[str] = None,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        feedback_doc = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "conversation_id": ObjectId(conversation_id)
            if isinstance(conversation_id, str)
            else conversation_id,
            "content": content,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "themes": themes or [],
            "created_at": datetime.utcnow(),
        }
        result = self.feedback_collection.insert_one(feedback_doc)
        feedback_doc["_id"] = result.inserted_id
        return feedback_doc

    def bulk_create_feedbacks(self, feedbacks: List[Dict[str, Any]]) -> bool:
        if not feedbacks:
            return False
        now = datetime.utcnow()
        for fb in feedbacks:
            if "user_id" in fb and isinstance(fb["user_id"], str):
                fb["user_id"] = ObjectId(fb["user_id"])
            if "conversation_id" in fb and isinstance(fb["conversation_id"], str):
                fb["conversation_id"] = ObjectId(fb["conversation_id"])
            if "created_at" not in fb:
                fb["created_at"] = now
            if "themes" not in fb:
                fb["themes"] = []
            if "sentiment" not in fb:
                fb["sentiment"] = "neutral"
            if "sentiment_score" not in fb:
                fb["sentiment_score"] = 0.5

        result = self.feedback_collection.insert_many(feedbacks)
        return len(result.inserted_ids) > 0

    def get_user_feedbacks(self, user_id: str, limit: int = None) -> List[Dict]:
        query = {"user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id}
        cursor = self.feedback_collection.find(query).sort("created_at", -1)
        if limit is not None:
            cursor = cursor.limit(limit)
        feedbacks = list(cursor)

        question_keywords = [
            "what",
            "how",
            "should i",
            "which",
            "could you",
            "tell me",
            "?",
        ]

        filtered = []
        for feedback in feedbacks:
            content = feedback.get("content", "").lower()
            if (
                not any(keyword in content for keyword in question_keywords)
                or len(content) > 100
            ):
                filtered.append(feedback)
        return filtered

    def get_feedback_by_id(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        return self.feedback_collection.find_one({"_id": ObjectId(feedback_id)})

    def get_feedbacks_by_conversation(
        self, conversation_id: str
    ) -> List[Dict[str, Any]]:
        return list(self.feedback_collection.find({"conversation_id": conversation_id}))

    def delete_feedback(self, feedback_id: str) -> bool:
        result = self.feedback_collection.delete_one({"_id": ObjectId(feedback_id)})
        return result.deleted_count > 0

    def save_analysis(
        self,
        user_id: str,
        analysis: FeedbackAnalysis,
        feedback_count: int,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        analysis_doc = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "conversation_id": ObjectId(conversation_id)
            if isinstance(conversation_id, str)
            else conversation_id,
            "analysis": analysis.model_dump(),
            "feedback_count": feedback_count,
            "created_at": datetime.utcnow(),
        }
        result = self.analysis_collection.insert_one(analysis_doc)
        analysis_doc["_id"] = result.inserted_id
        return analysis_doc

    def get_latest_analysis(
        self, user_id: str, conversation_id: str = None
    ) -> Optional[Dict[str, Any]]:
        query = {"user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id}
        if conversation_id:
            query["conversation_id"] = (
                ObjectId(conversation_id)
                if isinstance(conversation_id, str)
                else conversation_id
            )
        return self.analysis_collection.find_one(query, sort=[("created_at", -1)])

    def get_user_analyses(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = (
            self.analysis_collection.find(
                {"user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id}
            )
            .sort("created_at", -1)
            .limit(limit)
        )
        return list(cursor)

    def create_conversation(
        self, user_id: str, title: str = "Feedback Analysis"
    ) -> Dict[str, Any]:
        conversation_doc = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "title": title,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.conversation_collection.insert_one(conversation_doc)
        conversation_doc["_id"] = result.inserted_id
        return conversation_doc

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.conversation_collection.find_one(
                {"_id": ObjectId(conversation_id)}
            )
        except Exception:
            return None

    def get_user_conversations(
        self, user_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        cursor = (
            self.conversation_collection.find(
                {"user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id}
            )
            .sort("updated_at", -1)
            .limit(limit)
        )
        return list(cursor)

    def update_conversation(self, conversation_id: str, title: str = None) -> bool:
        update_doc = {"updated_at": datetime.utcnow()}
        if title:
            update_doc["title"] = title
        try:
            result = self.conversation_collection.update_one(
                {"_id": ObjectId(conversation_id)}, {"$set": update_doc}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def create_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        message_doc = {
            "conversation_id": ObjectId(conversation_id)
            if isinstance(conversation_id, str)
            else conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.utcnow(),
        }
        result = self.message_collection.insert_one(message_doc)
        message_doc["_id"] = result.inserted_id

        try:
            self.conversation_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"updated_at": datetime.utcnow()}},
            )
        except Exception:
            pass

        return message_doc

    def get_conversation_messages(
        self, conversation_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        try:
            cursor = (
                self.message_collection.find(
                    {
                        "conversation_id": ObjectId(conversation_id)
                        if isinstance(conversation_id, str)
                        else conversation_id
                    }
                )
                .sort("created_at", 1)
                .limit(limit)
            )
            return list(cursor)
        except Exception:
            return []

    def get_sentiment_stats(self, user_id: str) -> Dict[str, int]:
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id)
                    if isinstance(user_id, str)
                    else user_id
                }
            },
            {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}},
        ]
        result = list(self.feedback_collection.aggregate(pipeline))
        stats = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
        for item in result:
            if item["_id"] in stats:
                stats[item["_id"]] = item["count"]
        return stats

    def get_theme_stats(self, user_id: str) -> List[Dict[str, Any]]:
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id)
                    if isinstance(user_id, str)
                    else user_id
                }
            },
            {"$unwind": "$themes"},
            {"$group": {"_id": "$themes", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        return list(self.feedback_collection.aggregate(pipeline))

    def get_feedback_count(self, user_id: str) -> int:
        return self.feedback_collection.count_documents(
            {"user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id}
        )

    def get_average_satisfaction(self, user_id: str) -> float:
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id)
                    if isinstance(user_id, str)
                    else user_id
                }
            },
            {"$group": {"_id": None, "avg_score": {"$avg": "$sentiment_score"}}},
        ]
        result = list(self.feedback_collection.aggregate(pipeline))
        return result[0]["avg_score"] if result else 0.5

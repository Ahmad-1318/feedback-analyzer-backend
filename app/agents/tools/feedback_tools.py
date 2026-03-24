from langchain.tools import tool
from app.core.database import get_database
from bson import ObjectId
import json


def create_feedback_tools(user_id: str, conversation_id: str):
    """
    Create tools scoped to CURRENT CONVERSATION ONLY.
    This makes queries fast and contextually relevant.
    """
    db = get_database()
    feedback_collection = db["feedbacks"]

    try:
        base_query = {
            "user_id": ObjectId(user_id)
            if isinstance(user_id, str) and ObjectId.is_valid(user_id)
            else user_id,
        }
        if conversation_id:
            base_query["conversation_id"] = (
                ObjectId(conversation_id)
                if isinstance(conversation_id, str)
                and ObjectId.is_valid(conversation_id)
                else conversation_id
            )
    except Exception:
        base_query = {"user_id": ObjectId(user_id)}

    @tool
    def get_all_feedbacks(limit: int = 500) -> str:
        """Get ALL feedback from the CURRENT session (Chat + CSV).
        Use this for general overview questions or counting feedback."""
        try:
            feedbacks = list(
                feedback_collection.find(base_query).sort("created_at", -1).limit(limit)
            )

            if not feedbacks:
                return json.dumps({"status": "no_data", "total": 0})

            stats = {
                "positive": sum(
                    1 for f in feedbacks if f.get("sentiment") == "positive"
                ),
                "negative": sum(
                    1 for f in feedbacks if f.get("sentiment") == "negative"
                ),
                "neutral": sum(1 for f in feedbacks if f.get("sentiment") == "neutral"),
                "mixed": sum(1 for f in feedbacks if f.get("sentiment") == "mixed"),
                "total_in_db": len(feedbacks),
            }

            formatted = [
                {
                    "content": f.get("content", "")[:200],
                    "sentiment": f.get("sentiment", "unknown"),
                }
                for f in feedbacks[:100]
            ]

            return json.dumps(
                {
                    "status": "success",
                    "stats": stats,
                    "samples": formatted,
                    "note": "Stats are for ALL data. Samples are the latest 100.",
                }
            )

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @tool
    def get_negative_feedbacks(limit: int = 100) -> str:
        """Get ONLY negative feedback from current conversation."""
        try:
            query = {**base_query, "sentiment": "negative"}
            feedbacks = list(
                feedback_collection.find(query).sort("created_at", -1).limit(limit)
            )
            formatted = [f.get("content", "") for f in feedbacks]
            return json.dumps(
                {"status": "success", "total": len(feedbacks), "feedbacks": formatted}
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @tool
    def get_positive_feedbacks(limit: int = 100) -> str:
        """Get ONLY positive feedback from current conversation."""
        try:
            query = {**base_query, "sentiment": "positive"}
            feedbacks = list(
                feedback_collection.find(query).sort("created_at", -1).limit(limit)
            )
            formatted = [f.get("content", "") for f in feedbacks]
            return json.dumps(
                {"status": "success", "total": len(feedbacks), "feedbacks": formatted}
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @tool
    def get_analytics_summary() -> str:
        """Get summary: satisfaction score, sentiment breakdown, top themes."""
        try:
            feedbacks = list(feedback_collection.find(base_query))
            if not feedbacks:
                return json.dumps({"status": "no_data"})

            total = len(feedbacks)
            sentiment_dist = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
            theme_counts = {}

            for f in feedbacks:
                sent = f.get("sentiment", "neutral")
                if sent in sentiment_dist:
                    sentiment_dist[sent] += 1
                for theme in f.get("themes", []):
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1

            satisfaction = (
                int(
                    (
                        (
                            sentiment_dist["positive"]
                            + sentiment_dist["mixed"] * 0.5
                            + sentiment_dist["neutral"] * 0.5
                        )
                        / total
                    )
                    * 100
                )
                if total > 0
                else 0
            )
            top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]

            return json.dumps(
                {
                    "status": "success",
                    "satisfaction_index": satisfaction,
                    "total_feedbacks": total,
                    "sentiment_distribution": sentiment_dist,
                    "top_themes": [{"theme": t, "count": c} for t, c in top_themes],
                }
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    return [
        get_all_feedbacks,
        get_negative_feedbacks,
        get_positive_feedbacks,
        get_analytics_summary,
    ]

from typing import Dict, Any, List
from datetime import datetime
from app.repositories.feedback_repository import FeedbackRepository


class AnalyticsService:
    def __init__(self, feedback_repo: FeedbackRepository):
        self.feedback_repo = feedback_repo

    def get_analytics_summary(self, user_id: str) -> Dict[str, Any]:
        all_feedbacks = self.feedback_repo.get_user_feedbacks(user_id, limit=None)
        if not all_feedbacks:
            return self._get_empty_analytics()
        total_feedbacks = len(all_feedbacks)
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
        for feedback in all_feedbacks:
            sentiment = feedback.get("sentiment", "neutral")
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            else:
                sentiment_counts["neutral"] += 1
        satisfaction_index = self._calculate_satisfaction_index(
            sentiment_counts, total_feedbacks
        )
        overall_sentiment = self._determine_overall_sentiment(sentiment_counts)
        theme_analysis = self._analyze_themes(all_feedbacks)
        for t in theme_analysis["themes"]:
            t["percentage"] = (
                int((t["count"] / total_feedbacks) * 100) if total_feedbacks > 0 else 0
            )
        latest_analysis_doc = self.feedback_repo.get_latest_analysis(user_id)
        feature_suggestions = []
        chat_response = ""
        if latest_analysis_doc:
            analysis_data = latest_analysis_doc.get("analysis", {})
            feature_suggestions = analysis_data.get("feature_suggestions", [])
            chat_response = analysis_data.get("chat_response", "")
        if not chat_response:
            chat_response = f"Analyzed {total_feedbacks} cumulative feedbacks. Overall {overall_sentiment} sentiment ({satisfaction_index}% satisfaction). Top theme: {theme_analysis['themes'][0]['theme'] if theme_analysis['themes'] else 'None'}."
        return {
            "satisfaction_index": satisfaction_index,
            "overall_sentiment": overall_sentiment,
            "detected_themes": len(theme_analysis["themes"]),
            "key_features_count": len(feature_suggestions),
            "total_feedbacks": total_feedbacks,
            "sentiment_distribution": sentiment_counts,
            "themes": theme_analysis["themes"],
            "theme_satisfaction": theme_analysis["theme_satisfaction"],
            "feature_suggestions": [
                {
                    "feature": fs.get("feature", ""),
                    "priority": fs.get("priority", "medium"),
                    "reasoning": fs.get("reasoning", ""),
                    "affected_users": fs.get("affected_users", 0),
                    "impact_score": fs.get("impact_score", 5.0),
                }
                for fs in feature_suggestions
            ],
            "chat_response": chat_response,
            "last_updated": datetime.utcnow().isoformat(),
        }

    def _calculate_satisfaction_index(
        self, sentiment_counts: Dict[str, int], total: int
    ) -> int:
        if total == 0:
            return 0
        score = (
            sentiment_counts["positive"] * 1.0
            + sentiment_counts.get("mixed", 0) * 0.5
            + sentiment_counts["neutral"] * 0.5
            + sentiment_counts["negative"] * 0.0
        ) / total
        return int(score * 100)

    def _determine_overall_sentiment(self, sentiment_counts: Dict[str, int]) -> str:
        if sentiment_counts["positive"] > sentiment_counts["negative"]:
            return "positive"
        elif sentiment_counts["negative"] > sentiment_counts["positive"]:
            return "negative"
        else:
            return "neutral"

    def _analyze_themes(self, feedbacks: List[Dict]) -> Dict[str, Any]:
        theme_sentiments = {}
        theme_examples = {}
        for feedback in feedbacks:
            themes = feedback.get("themes", [])
            sentiment = feedback.get("sentiment", "neutral")
            content = feedback.get("content", "")
            for theme in themes:
                if theme not in theme_sentiments:
                    theme_sentiments[theme] = {
                        "positive": 0,
                        "neutral": 0,
                        "negative": 0,
                        "mixed": 0,
                    }
                    theme_examples[theme] = []
                if sentiment in theme_sentiments[theme]:
                    theme_sentiments[theme][sentiment] += 1
                else:
                    theme_sentiments[theme]["neutral"] += 1
                if len(theme_examples[theme]) < 3:
                    theme_examples[theme].append(
                        content[:100] + "..." if len(content) > 100 else content
                    )
        themes_list = []
        theme_satisfaction_list = []
        for theme, sentiments in theme_sentiments.items():
            total = sum(sentiments.values())
            satisfaction = self._calculate_theme_satisfaction(sentiments, total)
            themes_list.append(
                {
                    "theme": theme,
                    "count": total,
                    "sentiment": self._get_dominant_sentiment(sentiments),
                    "examples": theme_examples[theme],
                    "satisfaction": satisfaction,
                    "percentage": 0,
                }
            )
            theme_satisfaction_list.append(
                {"theme": theme, "satisfaction": satisfaction}
            )
        themes_list.sort(key=lambda x: x["count"], reverse=True)
        theme_satisfaction_list.sort(key=lambda x: x["satisfaction"], reverse=True)
        return {
            "themes": themes_list,
            "theme_satisfaction": theme_satisfaction_list[:10],
        }

    def _calculate_theme_satisfaction(
        self, sentiments: Dict[str, int], total: int
    ) -> int:
        if total == 0:
            return 50
        score = (
            sentiments["positive"] * 1.0
            + sentiments.get("mixed", 0) * 0.5
            + sentiments["neutral"] * 0.5
            + sentiments["negative"] * 0.0
        ) / total
        return int(score * 100)

    def _get_dominant_sentiment(self, sentiments: Dict[str, int]) -> str:
        pos = sentiments.get("positive", 0)
        neg = sentiments.get("negative", 0)
        if pos > 0 and neg > 0:
            ratio = pos / (pos + neg)
            if ratio > 0.7:
                return "positive"
            if ratio < 0.3:
                return "negative"
            return "mixed"
        if pos > neg:
            return "positive"
        elif neg > pos:
            return "negative"
        else:
            return "neutral"

    def get_historical_analytics(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        analyses = self.feedback_repo.get_user_analyses(user_id, limit=limit)
        if not analyses:
            return {"history": [], "trend": "stable", "average_satisfaction": 0}
        history = []
        satisfaction_scores = []
        for analysis_doc in analyses:
            analysis_data = analysis_doc.get("analysis", {})
            satisfaction = analysis_data.get("satisfaction_index", 0.5)
            satisfaction_scores.append(satisfaction)
            history.append(
                {
                    "date": analysis_doc.get("created_at"),
                    "satisfaction_index": int(satisfaction * 100),
                    "feedback_count": analysis_doc.get("feedback_count", 0),
                    "themes_count": analysis_data.get("total_themes_detected", 0),
                    "sentiment": analysis_data.get("overall_sentiment", "neutral"),
                }
            )
        avg_satisfaction = (
            sum(satisfaction_scores) / len(satisfaction_scores)
            if satisfaction_scores
            else 0.5
        )
        trend = "stable"
        if len(satisfaction_scores) >= 2:
            current = satisfaction_scores[0]
            previous = satisfaction_scores[1]
            if current > previous + 0.05:
                trend = "improving"
            elif current < previous - 0.05:
                trend = "declining"
        return {
            "history": history,
            "trend": trend,
            "average_satisfaction": int(avg_satisfaction * 100),
        }

    def get_theme_breakdown(self, user_id: str) -> Dict[str, Any]:
        all_feedbacks = self.feedback_repo.get_user_feedbacks(user_id, limit=None)
        if not all_feedbacks:
            return {
                "themes": [],
                "sentiment_stats": {"positive": 0, "neutral": 0, "negative": 0},
                "total_feedbacks": 0,
            }
        theme_analysis = self._analyze_themes(all_feedbacks)
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
        for f in all_feedbacks:
            s = f.get("sentiment", "neutral")
            if s in sentiment_counts:
                sentiment_counts[s] += 1
        total = len(all_feedbacks)
        themes = theme_analysis["themes"]
        for t in themes:
            t["percentage"] = int((t["count"] / total) * 100) if total > 0 else 0
        return {
            "themes": themes,
            "sentiment_stats": sentiment_counts,
            "total_feedbacks": total,
        }

    def get_recommendations(self, user_id: str) -> Dict[str, Any]:
        latest_analysis_doc = self.feedback_repo.get_latest_analysis(user_id)
        if not latest_analysis_doc:
            return {"critical": [], "high": [], "medium": [], "low": []}
        analysis_data = latest_analysis_doc.get("analysis", {})
        feature_suggestions = analysis_data.get("feature_suggestions", [])
        grouped = {"critical": [], "high": [], "medium": [], "low": []}
        for fs in feature_suggestions:
            priority = fs.get("priority", "medium").lower()
            item = {
                "feature": fs.get("feature", ""),
                "reasoning": fs.get("reasoning", ""),
                "affected_users": fs.get("affected_users", 0),
                "impact_score": fs.get("impact_score", 5.0),
            }
            if priority in grouped:
                grouped[priority].append(item)
            else:
                grouped["medium"].append(item)
        return grouped

    def _get_empty_analytics(self) -> Dict[str, Any]:
        return {
            "satisfaction_index": 0,
            "overall_sentiment": "neutral",
            "detected_themes": 0,
            "key_features_count": 0,
            "total_feedbacks": 0,
            "sentiment_distribution": {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "mixed": 0,
            },
            "themes": [],
            "theme_satisfaction": [],
            "feature_suggestions": [],
            "chat_response": "No feedback analyzed yet. Submit customer feedback to get started.",
            "last_updated": None,
        }

from src.bots.visitor_bot import VisitorBot
from unittest.mock import MagicMock

def test_fit_score():
    # Mock config
    config = MagicMock()
    config.visitor.keywords = ["Python", "DevOps"]

    bot = VisitorBot(config=config, profiles_limit_override=1)

    # Case 1: Perfect Match
    data_high = {
        "skills": ["Python", "Docker", "Kubernetes"],
        "headline": "Senior DevOps Engineer | Python Expert",
        "summary": "Experienced with AWS and Azure",
        "certifications": ["AWS Solutions Architect", "CKA"],
        "years_experience": 10
    }
    score_high = bot._calculate_fit_score(data_high)
    print(f"High Score: {score_high}")
    assert score_high > 80, "Expected high score"

    # Case 2: Low Match
    data_low = {
        "skills": ["Java", "Spring"],
        "headline": "Java Developer",
        "summary": "",
        "certifications": [],
        "years_experience": 2
    }
    score_low = bot._calculate_fit_score(data_low)
    print(f"Low Score: {score_low}")
    assert score_low < 50, "Expected low score"

if __name__ == "__main__":
    test_fit_score()
    print("Fit Score Test Passed!")

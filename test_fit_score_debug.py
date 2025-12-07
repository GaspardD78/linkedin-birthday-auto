from src.bots.visitor_bot import VisitorBot
from unittest.mock import MagicMock

def test_fit_score():
    config = MagicMock()
    config.visitor.keywords = ["Python", "DevOps"]

    bot = VisitorBot(config=config, profiles_limit_override=1)

    data_high = {
        "skills": ["Python", "Docker", "Kubernetes"],
        "headline": "Senior DevOps Engineer | Python Expert",
        "summary": "Experienced with AWS and Azure",
        "certifications": ["AWS Solutions Architect", "CKA"],
        "years_experience": 10
    }

    # We want to trace the score components
    # 1. Keywords (Python, DevOps)
    # Corpus: "python docker kubernetes senior devops engineer | python expert experienced with aws and azure"
    # Matches: Python (twice), DevOps (once). Total distinct matches = 2.
    # Score logic: matches > 0 => matches * 10 (capped at 40). 2*10 = 20 pts.
    # Wait, the prompt said: "Compétences techniques (ex: Azure, C#) : 40 pts."

    # 2. Experience (10 years)
    # exp >= 5 => 20 pts.

    # 3. Certifications (AWS, CKA)
    # "aws" in certs string? Yes.
    # Matches: AWS. 1 match * 10 = 10 pts.
    # CKA not in key_certs list in code ("azure", "aws", "gcp", "kubernetes", "docker", "terraform", "scrum", "pmp")?
    # Actually CKA is Kubernetes. But let's check code logic.

    # 4. Open to work
    # Headline does not have "open to work".

    # Total so far: 20 + 20 + 10 = 50.
    # We need > 80 for "High Score".

    # To get 80, we need more keyword matches or "Open to Work".

    score = bot._calculate_fit_score(data_high)
    print(f"Detailed Score: {score}")

if __name__ == "__main__":
    test_fit_score()

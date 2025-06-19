# agents.py

class Researcher:
    def __init__(self, unique_id, max_yearly_reviews, model):
        self.unique_id = unique_id
        self.model = model
        self.status = "L"  # Lazy
        self.prev_status = "L"  # Lazy
        self.num_tokens = model.initial_tokens
        self.papers_to_submit = []
        self.papers_to_review = []
        self.reviews_done = []
        self.papers_submitted = []
        self.max_yearly_reviews = max_yearly_reviews

    def step(self):
        self.model.agent_actions(self)

class Paper:
    def __init__(self, ID, generation_step, submission_step, author_id, num_reviews):
        self.ID = ID
        self.generation_step = generation_step
        self.submission_step = submission_step
        self.author_id = author_id
        self.num_reviews = num_reviews
        self.reviewers = []
        self.reviewers_invited = []
        self.num_invites = 0

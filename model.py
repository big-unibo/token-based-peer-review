import math
import numpy as np
import time
import datetime
import logging
from mesa import Model
from mesa.datacollection import DataCollector
from agents import Researcher, Paper
import random


import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (8, 4)

class JournalModel(Model):
    def __init__(
        self,
        num_authors=135972,
        backlog_of_papers_to_review=0,
        initial_tokens=3,
        daily_submission_prob=0.023,
        prob_2_reviews=0.73,
        prob_accept_L=0.20,
        prob_accept_E=1.00,
        verbose_logging=False,
        no_tokens_to_submit=False,
        num_invites_per_review=1,
        num_days_with_no_tokens_needed=365,
        num_days_with_no_stats=0,
        max_yearly_reviews_per_author=0,
        max_yearly_reviews_per_author_distribution="Yes",
        simulator=None,
    ):
        super().__init__()

        # Logs
        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        log_fname = f"log-{timestamp}.txt"
        self.logger = logging.getLogger(f"JournalModel-{timestamp}")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_fname, mode="w")
        fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
        self.logger.addHandler(fh)
        # optional: prevent double‐logging to root
        self.logger.propagate = False

        # CSV
        self.csv_fname = f"csv-{timestamp}.csv"
        self.csv_file = open(self.csv_fname, "w")

        self.csv_file.write(
            "Step,Submitted,Submitted waiting reviewers,Submitted in review,Avg reviewing time 1y,Avg reviewing time 1m,Avg invites per paper 1y,Avg invites per paper 1m\n"
        )
        self.csv_file.flush()

        self.simulator = simulator
        if self.simulator is not None:
            self.simulator.setup(self)

        self.num_authors = num_authors
        self.backlog_of_papers_to_review = backlog_of_papers_to_review
        self.initial_tokens = initial_tokens
        self.daily_submission_prob = daily_submission_prob
        self.prob_2_reviews = prob_2_reviews
        self.prob_accept_review_invitation = {"L": prob_accept_L, "E": prob_accept_E}
        self.verbose_logging = verbose_logging
        self.no_tokens_to_submit = no_tokens_to_submit
        self.num_invites_per_review = num_invites_per_review
        self.num_days_with_no_tokens_needed=num_days_with_no_tokens_needed
        self.num_days_with_no_stats=num_days_with_no_stats
        self.max_yearly_reviews_per_author=max_yearly_reviews_per_author
        self.max_yearly_reviews_per_author_distribution=max_yearly_reviews_per_author_distribution

        self.review_time = {
            "L": {10: 0.063, 20: 0.107, 30: 0.145, 40: 0.201, 50: 0.289,
                  60: 0.358, 70: 0.440, 80: 0.503, 90: 0.767, 100: 0.843,
                  110: 0.899, 120: 0.931, 130: 0.950, 140: 0.969, 170: 0.981,
                  180: 0.987, 200: 1.000},
            "E": {7: 1.000}
        }

        self.reviewers_distributions = { 
                10: 8386,
                11: 8119,
                12: 7852,
                13: 7586,
                14: 7319,
                15: 7052,
                16: 6786,
                17: 6519,
                18: 6252,
                19: 5986,
                20: 5719,
                21: 5452,
                22: 5186,
                23: 4919,
                24: 4652,
                25: 4387,
                26: 4119,
                27: 3852,
                28: 3586,
                29: 3319,
                30: 3052,
                31: 2786,
                32: 2519,
                33: 2252,
                34: 1986,
                35: 1719,
                36: 1452,
                37: 1186,
                38: 919,
                39: 652,
                40: 386
        }

        self.global_step = 0
        self.next_paper_id = 1
        self.submitted_papers = []
        self.submitted_papers_dict = {}  ### maps paper_id to paper object
        self.submitted_papers_missing_reviewers = 0

        self.sum_count_rev_time_per_paper = (0,0)
        self.avg_rev_time_per_paper_1y = 0
        self.avg_rev_time_per_paper_1m = 0
        self.avg_invites_per_paper_1y = 0
        self.avg_invites_per_paper_1m = 0
        self.moving_average_rev_time_dict = dict()
        self.moving_average_inv_per_pap_dict = dict()

        self.researchers = dict()
        if(self.max_yearly_reviews_per_author_distribution=="Yes"):
            yearly_reviews_to_be_stable = int(365 * self.daily_submission_prob * (3 - self.prob_2_reviews))
            for (k,v) in self.reviewers_distributions.items():
                for j in range(v):
                    i = len(self.researchers)
                    self.researchers[i] = Researcher(i, k, self)
                    # self.logger.debug(f"Adding researcher {i} with {k} yearly reviews")
            for i in range(len(self.researchers), self.num_authors):
                self.researchers[i] = Researcher(i, yearly_reviews_to_be_stable, self)
                # self.logger.debug(f"Adding researcher {i} with {yearly_reviews_to_be_stable} yearly reviews to be stable")
            # self.logger.debug(f"Total {len(self.researchers)} reviewers")
        else:
            self.researchers = {i: Researcher(i, 0, self) for i in range(self.num_authors)}

        
 
        self.datacollector = DataCollector(
            model_reporters={
                "Submitted": lambda m: len(m.submitted_papers),
                "Submitted waiting reviewers": lambda m: m.submitted_papers_missing_reviewers,
                "Submitted in review": lambda m: len(m.submitted_papers)-m.submitted_papers_missing_reviewers,
                "Avg reviewing time 1y": lambda m: m.avg_rev_time_per_paper_1y,
                "Avg reviewing time 1m": lambda m: m.avg_rev_time_per_paper_1m,
                "Avg invites per paper 1y": lambda m: m.avg_invites_per_paper_1y,
                "Avg invites per paper 1m": lambda m: m.avg_invites_per_paper_1m,
            }
        )
        self.datacollector.collect(self)      

        self.running = True

    def verboseLog(self, msg):
        if self.verbose_logging:
            self.logger.debug(msg)

    def coin_toss(self, distribution):
        n = random.random()
        for k, v in sorted(distribution.items()):
            if v >= n:
                return k
        return max(distribution.keys())

    def step(self):
        
        ##########
        ## INITIALIZE METRICS
        ##########
        if(self.global_step == 0):
            self.datacollector.collect(self)
        self.global_step += 1
        self.reviews_done_in_step = 0
        self.reviews_done_in_step_per_status = dict()
        self.papers_with_reviews_comleted_in_step = 0
        self.papers_submitted_in_step = 0
        self.papers_generated_in_step = 0
        self.papers_waiting_for_tokens = 0
        self.papers_waiting_for_tokens_dict = dict()
        self.inviting_lazy_in_step = False
        self.missing_reviews = 0
        self.avg_yearly_reviews_per_reviewer = 0
        self.var_yearly_reviews_per_reviewer = 0
        self.std_yearly_reviews_per_reviewer = 0
        self.avg_yearly_generations_per_author = 0
        self.var_yearly_generations_per_author = 0
        self.std_yearly_generations_per_author = 0
        self.num_transition_e2l = 0
        self.num_transition_l2e = 0
        self.num_transition_l2e2l = 0

        self.moving_average_rev_time_dict[self.global_step] = (0,0)
        self.moving_average_inv_per_pap_dict[self.global_step] = (0,0)
        self.moving_average_rev_per_res = []
        self.moving_average_gen_per_aut = []
        
        self.reviews_anticipated = 0
        self.reviews_anticipated_dict = dict()

        self.heatmap_rev_vs_gen = dict()
        self.heatmap_rev_vs_max = dict()

        ##########
        ## RUN SIMULATION
        ##########
        self.verboseLog(f"*** Step {self.global_step} started ***")
    
        for researcher in self.researchers.values():
            researcher.step()

        self.assign_reviews()

        ##########
        ## COLLECT METRICS
        ##########

        if(self.global_step <= self.num_days_with_no_stats):
            self.sum_count_sub_time_per_paper = (0,0)
            self.sum_count_rev_time_per_paper = (0,0)
            self.sum_count_rev_time_per_paper_and_status = dict()
            self.avg_sub_time_per_paper = 0
            self.avg_rev_time_per_paper = 0
            self.avg_rev_time_per_paper_and_status = dict()
            self.tot_invites = 0
            self.avg_invites_per_paper = 0

        self.avg_rev_time_per_paper_1y = sum([v[1] for (k,v) in self.moving_average_rev_time_dict.items() if k >= self.global_step-365]) / sum([v[0] for (k,v) in self.moving_average_rev_time_dict.items() if k >= self.global_step-365]) if sum([v[0] for (k,v) in self.moving_average_rev_time_dict.items() if k >= self.global_step-365]) > 0 else 0
        self.avg_rev_time_per_paper_1m = sum([v[1] for (k,v) in self.moving_average_rev_time_dict.items() if k >= self.global_step-30]) / sum([v[0] for (k,v) in self.moving_average_rev_time_dict.items() if k >= self.global_step-30]) if sum([v[0] for (k,v) in self.moving_average_rev_time_dict.items() if k >= self.global_step-365]) > 0 else 0

        self.avg_invites_per_paper_1y = sum([v[1] for (k,v) in self.moving_average_inv_per_pap_dict.items() if k >= self.global_step-365]) / sum([v[0] for (k,v) in self.moving_average_inv_per_pap_dict.items() if k >= self.global_step-365]) if sum([v[0] for (k,v) in self.moving_average_inv_per_pap_dict.items() if k >= self.global_step-365]) > 0 else 0
        self.avg_invites_per_paper_1m = sum([v[1] for (k,v) in self.moving_average_inv_per_pap_dict.items() if k >= self.global_step-30]) / sum([v[0] for (k,v) in self.moving_average_inv_per_pap_dict.items() if k >= self.global_step-30]) if sum([v[0] for (k,v) in self.moving_average_inv_per_pap_dict.items() if k >= self.global_step-365]) > 0 else 0
        
        self.submitted_papers_missing_reviewers = len(self.submitted_papers)
        for paper in self.submitted_papers[:]:
            if len(paper.reviewers) == paper.num_reviews:
                self.submitted_papers_missing_reviewers -= 1

        self.datacollector.collect(self)
        
        self.csv_file.write(
            f"{self.global_step},{len(self.submitted_papers)},{self.submitted_papers_missing_reviewers},{len(self.submitted_papers)-self.submitted_papers_missing_reviewers},{self.avg_rev_time_per_paper_1y},{self.avg_rev_time_per_paper_1m},{self.avg_invites_per_paper_1y},{self.avg_invites_per_paper_1m}\n"
        )
        self.csv_file.flush()

    def tokens_needed_to_submit(self):
        if self.no_tokens_to_submit:
            return False
        else:
            return self.global_step-self.num_days_with_no_tokens_needed > 0


    def agent_actions(self, agent):

        # CREATE A NEW PAPER
        n = random.random()
        if n < self.daily_submission_prob:
            new_paper = Paper(
                ID=self.next_paper_id,
                generation_step=self.global_step,
                submission_step=None,
                author_id=agent.unique_id,
                num_reviews=self.coin_toss({2: self.prob_2_reviews, 3: 1.0}),
            )
            self.next_paper_id += 1
            # self.papers_generated_in_step += 1
            agent.papers_to_submit.append(new_paper)
            self.verboseLog(f'Agent {agent.unique_id} wrote a new paper ({n}<{self.daily_submission_prob}) with {new_paper.num_reviews} reviews needed; now has {len(agent.papers_to_submit)} papers to submit')
        else:
            self.verboseLog(f'Agent {agent.unique_id} did not write a new paper ({n}>={self.daily_submission_prob})')

        # DO REVIEWS AND EARN TOKENS
        reviews_done = []
        for idx, (paper_id, scheduled_step, done_by_status, accepted_step) in enumerate(agent.papers_to_review):
            if scheduled_step == self.global_step:
                paper = self.submitted_papers_dict.get(paper_id)
                if paper:
                    for j, (rid, done) in enumerate(paper.reviewers):
                        if rid == agent.unique_id:
                            paper.reviewers[j] = (agent.unique_id, self.global_step)
                            if self.tokens_needed_to_submit():
                                agent.num_tokens += 1
                            self.verboseLog(f'Agent {agent.unique_id} reviewed paper {paper_id} and now has {agent.num_tokens} tokens')

                            self.moving_average_rev_time_dict[self.global_step] = (self.moving_average_rev_time_dict[self.global_step][0] + 1, self.moving_average_rev_time_dict[self.global_step][1] + (self.global_step - accepted_step))
                        else:
                            self.verboseLog(f'ERROR - Agent {agent.unique_id} was supposed to review paper {paper_id} but agent''s id was not found in the list of reviewers {paper.reviewers}')
                else:
                    self.verboseLog(f'ERROR - Agent {agent.unique_id} was supposed to review paper {paper_id} but paper''s id was not found in the global list of submitted papers')
                reviews_done.append((paper_id, scheduled_step, done_by_status, accepted_step))
            elif scheduled_step > self.global_step:
                self.verboseLog(f'Agent {agent.unique_id} has not yet reviewed paper {paper_id} (scheduled for step {scheduled_step}; current is {self.global_step})')
        for rev in reviews_done: 
            agent.reviews_done.append(rev)
            agent.papers_to_review.remove(rev)

        # SUBMIT PAPERS AND SPEND TOKENS
        papers_ready = []
        for paper in agent.papers_to_submit:
            if not self.tokens_needed_to_submit():
                paper.submission_step = self.global_step
                self.submitted_papers.append(paper)
                self.submitted_papers_dict[paper.ID] = paper
                papers_ready.append(paper)
                self.verboseLog(f'Agent {agent.unique_id} submitted paper {paper.ID} spending {paper.num_reviews} tokens and now has {agent.num_tokens} tokens')
            else:
                if paper.num_reviews <= agent.num_tokens:
                    paper.submission_step = self.global_step
                    self.submitted_papers.append(paper)
                    agent.num_tokens -= paper.num_reviews
                    self.submitted_papers_dict[paper.ID] = paper
                    papers_ready.append(paper)
                    self.verboseLog(f'Agent {agent.unique_id} submitted paper {paper.ID} spending {paper.num_reviews} tokens and now has {agent.num_tokens} tokens')
                else:
                    self.verboseLog(f'Agent {agent.unique_id} has not enough tokens to submit paper {paper.ID} ({agent.num_tokens} available tokens < {paper.num_reviews} required tokens)')
        for paper in papers_ready:
            agent.papers_to_submit.remove(paper)
            agent.papers_submitted.append(paper)

        # UPDATE LAZY/EAGER STATUS
        agent.prev_status = agent.status
        agent.became_eager = False

        if self.author_needs_reviews_to_publish(agent):
            rev_ant = 0
            
            self.verboseLog(f'Agent {agent.unique_id} has {len(agent.papers_to_submit)} papers to submit, with {self.get_author_tokens_to_submit(agent)} tokens needed, but has only {agent.num_tokens} tokens')
            token_needed = self.get_author_tokens_to_submit(agent) - agent.num_tokens
            for idx, (paper_id, scheduled_step, done_by_status, accepted_step) in enumerate(agent.papers_to_review):
                if token_needed <= 0:
                    break
                agent.became_eager = True
                #add jitter to the review time of up to 10 days
                new_review_time = self.global_step + self.coin_toss(self.review_time[agent.status]) + random.randint(0, 10)
                if scheduled_step > new_review_time:
                    agent.papers_to_review[idx] = (paper_id, new_review_time, "E", accepted_step)
                    token_needed -= 1
                    self.verboseLog(f'Agent {agent.unique_id} updated review time for paper {paper_id} to {new_review_time} because needs reviews to publish')
                    rev_ant += 1
                else:
                    agent.papers_to_review[idx] = (paper_id, scheduled_step, "E", accepted_step)
                    self.verboseLog(f'Agent {agent.unique_id} did not update review time for paper {paper_id} because it is already scheduled in {scheduled_step-self.global_step} days')
            if token_needed > 0:
                agent.status = "E"
                self.verboseLog(f'Agent {agent.unique_id} is EAGER because still needs {token_needed} papers to submit and has no assigned review for it')              

        else:
            agent.status = "L"
            self.verboseLog(f'Agent {agent.unique_id} is LAZY because has {len(agent.papers_to_submit)} papers to submit, with {self.get_author_tokens_to_submit(agent)} tokens needed, has {agent.num_tokens} tokens and {len(agent.papers_to_review)} papers planned to review')

        self.clear_researcher_papers(agent)
        self.moving_average_rev_time_dict = {k: v for k, v in self.moving_average_rev_time_dict.items() if k >= self.global_step - 366}

    def get_author_tokens_to_submit(self,author):
        if not self.tokens_needed_to_submit():
            return 0
        tokens_to_submit = 0
        for paper in author.papers_to_submit:
            tokens_to_submit += paper.num_reviews
        return tokens_to_submit

    def get_author_tokens_needed(self,author):
        return self.get_author_tokens_to_submit(author) - author.num_tokens - len(author.papers_to_review)
    
    def author_needs_tokens(self,author):
        return self.get_author_tokens_needed(self,author) > 0
    
    def author_needs_reviews_to_publish(self,author):
        return self.get_author_tokens_to_submit(author) - author.num_tokens > 0
    
    def clear_researcher_papers(self, author, back=365):
        author.reviews_done = [rev for rev in author.reviews_done if rev[3] >= self.global_step - back]  # keep only reviews done in the last 365 days
        author.papers_submitted = [paper for paper in author.papers_submitted if paper.generation_step >= self.global_step - back]  # keep only papers submitted in the last 365 days
    
    def get_reviewers_reviews_in_timeframe(self, author, back=365, forward=0):
        return sum([1 for paper_id, scheduled_step, done_by_status, accepted_step in author.papers_to_review if accepted_step >= self.global_step - back]) \
                + sum([1 for paper_id, scheduled_step, done_by_status, accepted_step in author.reviews_done if accepted_step >= self.global_step - back])
    
    def get_authors_generations_in_timeframe(self, author, back=365, forward=0):
        return sum([1 for paper in author.papers_submitted if paper.generation_step >= self.global_step - back]) \
                + sum([1 for paper in author.papers_to_submit if paper.generation_step >= self.global_step - back])
    
    def reviewer_can_review(self,author):
        return author.max_yearly_reviews==0 or author.status=="E" or self.get_reviewers_reviews_in_timeframe(author)<author.max_yearly_reviews # per author check
    
    def assign_reviews(self):
        # Get eager reviewer to give them priority
        eager_researchers = [researcher for researcher in self.researchers.values() if researcher.status=="E"]

        for paper in self.submitted_papers[:]:
            if len(paper.reviewers) < paper.num_reviews and paper.submission_step <= self.global_step + 4: # adding 4 days of delay to begin inviting
                self.verboseLog(f'Paper {paper.ID} needs {paper.num_reviews} reviews but has only {len(paper.reviewers)} reviewers; inviting more reviewers')
                needed = paper.num_reviews - len(paper.reviewers)
                for _ in range(needed):
                    invites = 0
                    while invites < self.num_invites_per_review:
                        # Probability to invite: used to model the fact that the reviewer takes some time to answer the invitation
                        if(random.random() >= 1/7):
                            break
                        invites += 1
                        paper.num_invites += 1
                        # Priority to eager reviewers
                        if len(eager_researchers)>0:
                            erid = random.randint(0, len(eager_researchers) - 1)
                            reviewer = self.researchers.get(eager_researchers[erid].unique_id)
                        else:
                            self.inviting_lazy_in_step = True
                            rid = random.randint(0, self.num_authors - 1)
                            reviewer = self.researchers.get(rid)
                        # Invite
                        if reviewer and self.reviewer_can_review(reviewer) and random.random() <= self.prob_accept_review_invitation[reviewer.status]:
                            #add jitter to the review time of up to 10 days
                            review_iter = self.coin_toss(self.review_time[reviewer.status]) + random.randint(0, 10)
                            reviewer.papers_to_review.append((paper.ID, self.global_step + review_iter, reviewer.status, self.global_step))
                            paper.reviewers.append((reviewer.unique_id, -1))
                            # reviewer.max_reviews -= 1
                            self.verboseLog(f'Paper {paper.ID} invited reviewer {reviewer.unique_id} who agreed to review it and will do so in {review_iter} days (reviewer is {reviewer.status})')
                            
                            if paper.num_reviews == len(paper.reviewers): # enough reviewers invited, collect stat
                                self.moving_average_inv_per_pap_dict[self.global_step] = (self.moving_average_inv_per_pap_dict[self.global_step][0] + 1, self.moving_average_inv_per_pap_dict[self.global_step][1] + paper.num_invites)

                            if reviewer.status == "E" and self.author_needs_reviews_to_publish(reviewer):
                                reviewer.status = "L"
                                self.verboseLog(f'Agent {reviewer.unique_id} changed status from EAGER to LAZY because has enough reviews')
                                # Remove eager reviewer from the list
                                eager_researchers.remove(reviewer)
                            break
                        else:
                            self.verboseLog(f'Paper {paper.ID} invited reviewer {reviewer.unique_id} who refused to review it (reviewer is {reviewer.status})')
            else:
                # check if all reviewers have done their reviews
                all_done = True
                for rid, done in paper.reviewers:
                    if done == -1:
                        all_done = False
                        break
                if all_done:
                    self.submitted_papers.remove(paper)
                    del self.submitted_papers_dict[paper.ID] 
                    self.verboseLog(f'Paper {paper.ID} was reviewed and removed from the submitted papers list')
                else:
                    self.verboseLog(f'Paper {paper.ID} is awaiting reviews')
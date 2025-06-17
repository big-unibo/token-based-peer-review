# From Volunteerism to Duty: Reforming Peer-Review with Tokens

This repository contains a simulator for a token-based peer-review system for scientific journals, relying on two fundamental rules:
1. To submit a paper, the author (or group of authors) must provide a number of tokens equal to the number of reviews required by the journal.
2. For each review made, the reviewer receives one token from the journal.

The simulator is a Python program based on [Mesa](https://mesa.readthedocs.io/latest/) and [Solara](https://solara.dev/).

## Quick start

Python 3.12 or higher is recommended. 

The required Python libraries are listed in the requirements.txt file:

```
pip install -r requirements.txt
```

To launch the simulator:

```
solara run app.py
```

This will launch a web application at [localhost:8765]().

## Parameters

The simulator provides the following parameters:

- *Number of researchers*: the number of agents in the simulation, which will act as authors and reviewers.
    - Default: 135978. 
    - This is based on DBLP statistics and corresponds to the number of active authors in 2024, divided by the average number of authors per paper; thus, each agent corresponds to a group of researchers.
- *Initial tokens per researcher*: the number of tokens assigned to each agent when the token-based mechanism is activated.
    - Default: 3. 
- *Daily paper generation probability*: the daily probability with which each agent generates a new paper to submit. 
    - Default: 0.023. 
    - This is based on DBLP statistics, so that the same amount of papers submitted in 2024 is generated in the simulation. The number of submitted papers is determined as the number of papers published in 2024 divided by the an acceptance rate of 0.19, which is the average acceptance rate collected from the websites of over 700 journals.
- *Probability of 2 (instead of 3) reviews*: the probability that a paper is submitted to a journal requiring 2 reviews instead of 3.
    - Default: 0.73. 
    - This is based on the average number of reviews declared on the websites of over 700 journals.
- *Probability of accepting invite (Lazy reviewer)*: the probability that a lazy reviewer (i.e., one who does not need tokens) accepts a reviewing invitation.
    - Default: 0.2. 
    - This is based on the average number of invites sent per review declared by the people interviewed in our survey.
- *Probability of accepting invite (Eager reviewer)*: the probability that an eager reviewer (i.e., one who needs tokens to submit a paper) accepts a reviewing invitation.
    - Default: 1.0. 
- *N. of daily invites per needed review*: the number of invites that an editor sends in a day for each review that must be assigned.
    - Default: 1. 
- *N. of days before tokens are enable*: the number of days after which the token-based mechanism is activated; before that, generated papers are automatically submitted.
    - Default: 1825 (5 years). 
    - An initialization period of 3+ years is recommended for the system to stabilize.
- *Enable max n. of yearly reviews per author*: if enabled, reviewers refuse any invitation if they have done *enough* reviews in the previous 365 days.
    - Default: yes. 
    - If enabled, the maximum number of yearly reviews per reviewer varies from 4 to 34; the distribution of this value to the researchers is made in a way to ensure that the yearly demand for reviews is met (considering the default number of researchers with the default probability of paper generation), ensuring the continuity of the system.
import solara
from mesa.visualization import SolaraViz, make_plot_component
import mesa.visualization.solara_viz as solviz
from model import JournalModel

import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (8, 4)

from matplotlib import colormaps
css = {
    "editor": colormaps["Set1"](1),
    "waitingRev": colormaps["Set1"](4),
    "underRev": colormaps["Set2"](5),
    "lazy": colormaps["Set1"](2),
    "eager": colormaps["Set1"](0),
    "done": colormaps["Set1"](3),
    "neutral": colormaps["Set1"](8),
    "total": 'black',
    "authorQueue": colormaps["Set1"](6),
}

# Monkey‐patch UserInputs to use numeric input fields instead of sliders
@solviz.solara.component

def UserInputs(user_params, on_change=None):
    """Extended UserInputs: support InputInt and InputFloat alongside existing types."""
    for name, options in user_params.items():
        def change_handler(value, name=name):
            on_change(name, value)

        # Preserve legacy Slider-based options
        if isinstance(options, solviz.Slider):
            slider_class = solara.SliderFloat if options.is_float_slider else solara.SliderInt
            slider_class(
                options.label,
                value=options.value,
                on_value=change_handler,
                min=options.min,
                max=options.max,
                step=options.step,
            )
            continue

        label = options.get("label", name)
        input_type = options.get("type")

        if input_type == "InputInt":
            solara.InputInt(
                label,
                value=options.get("value"),
                on_value=change_handler,
                continuous_update=True,
                clearable=False,
            )
        elif input_type == "InputFloat":
            solara.InputFloat(
                label,
                value=options.get("value"),
                on_value=change_handler,
                continuous_update=True,
                clearable=False,
            )
        elif input_type == "SliderInt":
            solara.SliderInt(
                label,
                value=options.get("value"),
                on_value=change_handler,
                min=options.get("min"),
                max=options.get("max"),
                step=options.get("step"),
            )
        elif input_type == "SliderFloat":
            solara.SliderFloat(
                label,
                value=options.get("value"),
                on_value=change_handler,
                min=options.get("min"),
                max=options.get("max"),
                step=options.get("step"),
            )
        elif input_type == "Select":
            solara.Select(
                label,
                value=options.get("value"),
                on_value=change_handler,
                values=options.get("values"),
            )
        elif input_type == "Checkbox":
            solara.Checkbox(
                label=label,
                value=options.get("value"),
                on_value=change_handler,
            )
        elif input_type == "InputText":
            solara.InputText(
                label=label,
                value=options.get("value"),
                on_value=change_handler,
            )
        else:
            raise ValueError(f"{input_type} is not a supported input type")

# Override the default UserInputs in SolaraViz
solviz.UserInputs = UserInputs

# Define user-adjustable parameters
model_params = {
    "num_authors": {
        "type": "InputInt",
        "value": 135972,
        "min": 10,
        "max": 200000,
        "step": 100,
        "label": "Number of researchers",
    },
    "initial_tokens": {
        "type": "InputInt",
        "value": 3,
        "min": 0,
        "max": 10,
        "step": 1,
        "label": "Initial tokens per researcher",
    },
    "daily_submission_prob": {
        "type": "InputFloat",
        "value": 0.023,
        "min": 0.0,
        "max": 0.1,
        "step": 0.001,
        "label": "Daily paper generation probability",
    },
    "prob_2_reviews": {
        "type": "InputFloat",
        "value": 0.73,
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "label": "Probability of 2 (instead of 3) reviews",
    },
    "prob_accept_L": {
        "type": "InputFloat",
        "value": 0.20,
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "label": "Probability of accepting invite (Lazy reviewer)",
    },
    "prob_accept_E": {
        "type": "InputFloat",
        "value": 1.00,
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "label": "Probability of accepting invite (Eager reviewer)",
    },
    # "verbose_logging": {
    #     "type": "Checkbox",
    #     "value": False,
    #     "label": "Verbose Logging",
    # },
    "num_invites_per_review": {
        "type": "InputInt",
        "value": 1,
        "min": 1,
        "max": 10,
        "step": 1,
        "label": "N. of daily invites per needed review",
    },
    "num_days_with_no_tokens_needed": {
        "type": "InputInt",
        "value": 365,
        "min": 0,
        "max": 365*5,
        "step": 1,
        "label": "N. of days before tokens are enabled",
    },
    "max_yearly_reviews_per_author_distribution": {
        "type": "Select",
        "values": ["Yes","No"],
        "label": "Enable max n. of yearly reviews per author",
    },
}

# Instantiate model with default values
model = JournalModel(
    num_authors=model_params["num_authors"]["value"],
    initial_tokens=model_params["initial_tokens"]["value"],
    daily_submission_prob=model_params["daily_submission_prob"]["value"],
    prob_accept_L=model_params["prob_accept_L"]["value"],
    prob_accept_E=model_params["prob_accept_E"]["value"],
)

# Enable automatic stepping in SolaraViz
model.running = True

# Create a single line plot with two series and legend via post_process
Queue = make_plot_component(
    ["Submitted", "Submitted waiting reviewers", "Submitted in review"],
    post_process=lambda ax: (
        ax.title.set_text("Editorial Queue"),
        ax.lines[0].set_color(css["editor"]),
        ax.lines[1].set_color(css["waitingRev"]),
        ax.lines[2].set_color(css["underRev"]),
        ax.legend(["Queue size", "Papers waiting for Reviewers", "Papers under Review"], loc="upper left"),
        ax.set_xlabel("Day"),
    )
)


Stats = make_plot_component(
    [
        "Avg reviewing time 1y",
        "Avg reviewing time 1m", 
     ],
    post_process=lambda ax: ( 
        ax.title.set_text("Average times"),
        ax.lines[0].set_color(css["done"]),
        ax.lines[1].set_color(css["done"]),
        ax.lines[1].set_linestyle("--"),
        ax.legend([
            "Reviewing time (1y avg)", 
            "Reviewing time (1m avg)",
        ], loc="upper left"),
        ax.set_xlabel("Day"),
    )
)

Invites = make_plot_component(
    ["Avg invites per paper 1y","Avg invites per paper 1m"],
    post_process=lambda ax: ( 
        ax.title.set_text("Invites per Paper and Yearly Reviews per Reviewer"),
        ax.lines[0].set_color(css["waitingRev"]),
        ax.lines[1].set_color(css["waitingRev"]),
        ax.lines[1].set_linestyle("--"),
        ax.legend(["Invites per Paper (avg 1y)","Invites per Paper (avg 1m)"], loc="upper left"),
        ax.set_xlabel("Day"),
    )
)

# Build the SolaraViz page
page = SolaraViz(
    model,
    components=[Queue,
                # Reviews,Papers,Delta,
                Stats,Invites,
                # Perc,Tokens
                ],
    model_params=model_params,
    name="Token-based peer-review",

)

page  # run with: solara run app.py
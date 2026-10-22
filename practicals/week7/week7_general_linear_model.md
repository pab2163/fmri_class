# Practical #7: General Linear Model

The goal of this practical is to help you get comfortable with the key ideas of a general linear model, which is a core concept for analyzing task fMRI data. 

This practical is centered around a jupyter notebook tutorial made by Tor Wager and Martin Lindquist. In general, it shows how we would fit a regression model to a single fMRI voxel to ask how that voxel's mean signal was different during two different task conditions (A vs. B; for example two different colors displaying on the screen during the scan).

It *does* have some matrix math involved. Do your best to work through this and understand the key concepts, and see below for some places where the matrix math is translated into code that may be a little simpler to read. 

Your assignment is to read the tutorial, try a few changes with the code and run a separate python simulation script, then to answer some questions about the simulation and GLM in general to make sure you are solidifying your knowledge of how these models generally work.

## 1: Read the Tutorial

Read through the tutorial at https://torwager.github.io/elements-of-fmri-tutorials/book/part4/labs/ch18-lab-python/ including running all code interactively. You can either run the code chunks within the tutorial itself or download it to run.


## 2: Download the tutorial file and make sure code runs

**Download the tutorial as a jupyter notebook file** (there is a download button to the top right of the page within the row of little icons to the left of the little rocket icon) and make sure all code runs from your computer. It should run if you are using the conda environment set up for this class a your kernel, but let me Paul if you have any issues running the code on your computer. 

## 3: Make the connection of the general linear model (GLM) to "regular regression" in python

There's a lot of matrix math going on in this tutorial/code that might look complicated, but this is really just a way of expressing regression concepts via matrices. We get the same answer if we use regression tools to fit a linear regression (e.g., via ordinary least squares) in the same way you might already be used to with R or Python.


* Find the first code chunk under the section "## Step 2 — Fit the GLM with ordinary least squares": this is the one where you solve for the beta estiamte using the OLS estimate with matrix math.
* Now, make a new chunk and paste in the code below. This uses the [scikit-learn](https://scikit-learn.org/stable/) python package to run a linear regression via OLS where the predictors are the convolved A and B regressors (from the matrix `X`) and the outcome (`y`) is the timeseries of the voxel's data. 


```python
from sklearn.linear_model import LinearRegression

reg = LinearRegression().fit(X[:, :2], y)     # just the A and B columns
beta_hat = np.append(reg.coef_, reg.intercept_)
print(beta_hat)
```

Try to make the connection between this regression fit and the matrix one above. How do these values of beta_hat (the estimates for the predictors of A and B) match with what was calculated in the above chunk using matrix math?

If you get an error here, you may need to install the [scikit-learn](https://scikit-learn.org/stable/) python package to your `fmri_class` conda environment. You can do so with the following command from the command line

```bash
conda activate fmri_class
pip install scikit-learn
```

## 3: Test what happens when you make the events much closer together in time

Towards the top of the notebook there is code that determines the onset times of events in condition A and condition B. They are nicely separated in time so that no event happens 

```python
onsets_A = [12, 40, 74, 96, 135, 162, 190, 224, 255, 288, 310, 331]   # Condition A onsets (s): 12 events
onsets_B =  [25, 58, 86, 118, 148, 175, 210, 240, 270, 300, 322, 345]   # Condition B onsets (s): 12 events
```

Now, update the times of onsets_B such that each onset is exactly 1.5 seconds after onsets_A (e.g., it would be `[13.5, 41.2, ...]`). Before running any code, what do you think will happen to your estimate of the contrast between A and B? Why?

Now, re-run the jupyter notebook, and see for yourself. Remember to check all the plot showing the X matrix (e.g., regressors for A and B), the beta estiamtes for A and B from the GLM, and the contrast estimate.

## 4: Systematically test what happens when events are spaced more closely together in time

Download the [glm_lag_simulation.py](glm_lag_simulation.py) script and inspect it. Here, we will systematically vary the lags between when stimuli in condition A and condition B appear with the following offsets (in seconds): `LAGS = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12]`. For each lag, we'll randomly generate data 100 times, and fit the GLM to each randomly generated dataset. As before, there is a "true" effect here of an A > B contrast of 0.4 (0.8 - 0.4). 

Now, run the script using your `fmri_class` conda environment and examine the output `glm_lag_simulation.png` file. 

## To submit on canvas:

Please submit responses to the following questions

1. Inspect the `glm_lag_simulation.png`. There are 4 panels, each of which show an important aspect of the task design or GLM on the y-axis as a function of the lag between A & B onset times. Write an interpretation of what each respective panel tells us. If you were going to design this A vs. B task, which lag would you choose, and why? 

2. What does it mean to *convolve* the stimulus regressors with the HRF? Why is this necessary?

3. How does a contrast (e.g., A > B) turn regression estimates into scientific tests of "task-related activation" in each voxel?

4. What is a t-value (statistically), what does a "t-value for a contrast" indicate? 



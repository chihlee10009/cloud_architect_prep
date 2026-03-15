Create an  web app in python using flask and tailwindcss for a modern sleek UI. 
The web app should allow me to quiz myself on the questions in the ref_cloud_architect_questions.md file.

Requirements:
0. the first screen should allow me to choose how many questions I want to answer for the quiz either as a regular quiz or a quiz based on the questions I have wrong that are still on the "Questions You Got Wrong" in the Performance Dashboard
1. I should be able to select multiple choice answers but do not show me the results until i submit the quiz like for a real test
2. The answers should have explanations for why each answer is correct or incorrect
3. keep track of correct vs incorrect answers across all of my quizzes and show me a score as a percentage in the performance dashboard 
3a. show how many questions in the questions.json file have been seen vs not seen 
4. Track the incorrect answers on the performance dashboard and add it to the appropriate "Performance Breakdown" on what question I got wrong. Keep track of When I get the question right on future quizzes, remove the question from the list after I answer it correctly three consequtive times in future quizzes
5.  Create a prompt to feed to notebooklm podcast so that I can learn more on that subject.
6. Add a section at the bottom of the "Performance Dashboard" that shows the question number and the question I got wrong across all of my quizzes.
7. If I answer a question successfully 3 consequtive times, across my quizzes, then do not ask that question again in future quizzes. This metric should also reset once the "Reset All" button is clicked
8. Allow me to select from the questions I got wrong in the "Questions You Got Wrong" of the Performance Dashboard and make sure they show up in the next quiz Create a button that allows me to take a quiz on just the questions I selected.
9. Make sure to add the questions I got wrong more frequently into future quizzes
10. Show a list of the questions I mastered in the "Performance Dashboard"
11. Create an option to create a quiz using questions that has not come up yet when i click "Take a Quiz"
12. Some of the questions in the study set is outdates and will not be worded the same on the 2026 Google Professional Cloud Architect exam. You are a Google Cloud Architect who recently passed the Professional Cloud Architect Certification. Reword the questions to reflect what would likely be on the 2026 Google Professional Cloud Architect exam. 
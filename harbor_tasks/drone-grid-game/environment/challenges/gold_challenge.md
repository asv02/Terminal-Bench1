# Gold Key Challenge

## Problem Statement
Three ladies and four men are a group of friends i.e. P, K, R, Q, J, V and X. Each one has a unique profession i.e. Lawyer, Travel Agent, Air-hostess, Doctor, Professor, Consultant and Jeweller and each one owns a different car i.e. Alto, Corolla, Santro, Lancer, Ikon, Scorpio and Esteem, not necessarily in that order. None of the ladies is a Consultant or a Lawyer. R is an Air-hostess and she owns an Ikon car, P owns a Scorpio. K is not a Doctor. J is a Jeweller and he owns Corolla. V is a Lawyer and does not own Alto. X is a Consultant and owns Santro, The Doctor owns Esteem car whereas the Professor owns Scorpio. The Travel Agent owns an Alto. None of the ladies owns a Scorpio.

## Questions-
Question 1. Who are the three ladies in the group?
Question 2. What car does Q own?
Question 3. Who owns the car Lancer?
Question 4. What is the profession of K?
## Output Format

Write your answer to `/app/solutions/gold_answer.json` in the following JSON format:
```json
{
  "1": "V, R, K",
  "2": "Ikon",
  "3": "P",
  "4": "Air-hostess"
}
```

Valid types: "Knight", "Knave", "Spy"

## Constraints

- There is exactly ONE valid solution that satisfies all statements
- Each person makes exactly 2 statements
- Knights' statements are always true
- Knaves' statements are always false
- Spies can make any combination of true/false statements

**WARNING: Wrong answer = INSTANT DEATH!**
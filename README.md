## Frankstein MVP for credit evaluation 
Frankstein describes an end to end pipeline for evaluating credit applications. It makes use of ASP in order to build decision trees for each stages. Furthermore, ASP is used for optimising the best weighed score based on previous application data. 

### Running the project 
To run the project you can simply pass run the main file with
```
uv run main.py

```

This runs the full evaluation sequence. 

To run the optimisation suite, first install the packages with 
```
uv sync
```
Then run the following:
```
uv run python -m clingcon src/data/application_data.lp src/encodings/finance_optimisation.lp
```
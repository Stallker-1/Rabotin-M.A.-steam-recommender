FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY . .

RUN python -c "from recommender.train_recommender import prepare_and_train; from pathlib import Path; prepare_and_train(Path('/app/data'), Path('/app/recommender/model.pkl'))"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
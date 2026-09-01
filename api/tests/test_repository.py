"""
test_repository.py — cobre repository.py, com foco em regressão pro bug
da Etapa 1 (carbs_g/fat_g rotulados como F/C trocados em today_totals()).
"""
from app.models import models as m
from app.services import repository as repo


def _make_user(db):
    user = repo.get_or_create_user(db, "5511999999999", name="Teste")
    return user


def test_today_totals_nao_troca_carbo_com_gordura(db):
    """Regressão: uma refeição com P41/F5/C69 tem que voltar como
    F5/C69 em today_totals() — não invertido."""
    user = _make_user(db)
    db.add(m.Meal(
        user_id=user.id,
        meal_type="almoco",
        description="arroz com feijão e frango",
        calories=497,
        protein_g=41,
        carbs_g=69,
        fat_g=5,
    ))
    db.commit()

    totals = repo.today_totals(db, user.id)

    assert totals["kcal"] == 497.0
    assert totals["P"] == 41.0
    assert totals["C"] == 69.0
    assert totals["F"] == 5.0


def test_today_totals_soma_multiplas_refeicoes(db):
    user = _make_user(db)
    db.add_all([
        m.Meal(user_id=user.id, meal_type="cafe", description="a",
               calories=200, protein_g=10, carbs_g=20, fat_g=5),
        m.Meal(user_id=user.id, meal_type="almoco", description="b",
               calories=300, protein_g=20, carbs_g=30, fat_g=10),
    ])
    db.commit()

    totals = repo.today_totals(db, user.id)

    assert totals["kcal"] == 500.0
    assert totals["P"] == 30.0
    assert totals["C"] == 50.0
    assert totals["F"] == 15.0


def test_today_totals_usuario_sem_refeicao_retorna_zeros(db):
    user = _make_user(db)
    totals = repo.today_totals(db, user.id)
    assert totals == {"kcal": 0.0, "P": 0.0, "F": 0.0, "C": 0.0, "agua_ml": 0.0}


def test_last_n_days_totals_tambem_nao_troca_carbo_com_gordura(db):
    user = _make_user(db)
    db.add(m.Meal(
        user_id=user.id,
        meal_type="almoco",
        description="arroz com feijão e frango",
        calories=497,
        protein_g=41,
        carbs_g=69,
        fat_g=5,
    ))
    db.commit()

    week = repo.last_n_days_totals(db, user.id, days=7)
    hoje = max(week.keys())

    assert week[hoje]["C"] == 69.0
    assert week[hoje]["F"] == 5.0


def test_list_meals_today_retorna_descricoes_de_hoje(db):
    user = _make_user(db)
    db.add(m.Meal(user_id=user.id, meal_type="almoco", description="arroz com frango",
                   calories=497, protein_g=41, carbs_g=69, fat_g=5))
    db.commit()

    meals = repo.list_meals_today(db, user.id)

    assert len(meals) == 1
    assert meals[0].description == "arroz com frango"


def test_has_workout_logged_today_falso_sem_registro(db):
    user = _make_user(db)
    assert repo.has_workout_logged_today(db, user.id) is False


def test_has_workout_logged_today_true_apos_registro(db):
    user = _make_user(db)
    db.add(m.ExerciseLog(user_id=user.id, workout_type="LOWER A", exercises=[], completed=True))
    db.commit()

    assert repo.has_workout_logged_today(db, user.id) is True


def test_seed_default_plans_e_idempotente(db):
    user = _make_user(db)
    repo.seed_default_plans(db, user)
    repo.seed_default_plans(db, user)  # não deve duplicar/errar

    db.refresh(user)
    assert user.plan_nutrition is not None
    assert user.plan_training is not None
    assert user.plan_training.protocolo["0"] == "UPPER A"

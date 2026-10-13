"""Import the food list into the app through its API.

Run from the frontend directory with the backend available at DIET_API, for
example: DIET_API=http://127.0.0.1:8000 .venv/bin/python scripts/import_foods.py
"""

import csv
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import client
from api.client import ApiError


# name | serving grams | carbs | protein | fat
FOOD_DATA = """
Abacate|100|6.0|1.2|8.4
Albumina Salto's|100|5.0|84.0|0.0
Alcatra|100|0.0|31.9|11.6
Alface|100|0.0|0.0|0.0
Amendoas|100|20.0|20.0|50.0
Amendoa Defumada|100|29.6|18.6|47.3
Amendoim|100|18.7|22.5|54.0
Amendoim - Grao Cru|100|20.3|27.2|43.9
Arroz Branco|100|28.1|2.5|0.2
Arroz Integral|100|25.0|3.0|1.0
Arroz Parboilisado|100|74.0|6.0|2.6
Aveia|100|66.6|13.9|8.5
Azeite|100|0.0|0.0|92.0
Abobrinha|100|3.0|1.1|0.2
Banana|100|23.0|1.0|0.0
Batata Inglesa|100|11.9|1.2|0.0
Batata Doce|100|28.0|2.0|1.0
Beterraba|100|10.0|1.0|0.0
Beterraba|100|10.0|1.0|0.0
Brocolis|100|4.4|2.3|0.1
Cacau em Pó|100|28.0|25.0|11.0
Caseina|100|0.0|72.0|1.0
Castanha de Caju|100|26.0|20.0|47.0
Castanha do Brasil/Para|100|15.1|14.5|63.5
Castanha Para|100|15.1|14.5|63.5
Cebola|100|8.9|1.7|0.1
Cenoura|100|11.0|1.0|0.0
Chá Verde|100|0.0|0.0|0.0
Chia|100|12.0|4.0|9.0
Chocolate em po|100|60.0|11.5|5.5
Clara de Ovo (1 Clara de Ovo = 33g)|100|0.0|9.9|0.0
Contra File [Cru]|100|0.0|24.0|6.0
Corpus Light|100|4.1|8.3|0.0
Cottage|50|1.1|6.2|1.8
Couve Refogada|100|10.3|2.6|9.1
Pimentao|100|5.5|1.2|0.2
Tortilha|100|55.6|9.0|7.1
Creatina|100|0.0|100.0|0.0
Creme de Ricota|100|0.0|13.0|7.0
Farinha de Aveia|100|67.0|14.9|7.0
Feijão Preto|100|24.0|9.0|1.0
Frango Cozido|100|0.0|32.0|2.5
Fruta|100|12.5|1.0|0.5
Grão de Bico|100|57.9|21.2|5.4
Glutamina|100|0.0|100.0|0.0
Iogurte Grego|90|13.0|4.9|6.4
Iogurte Integral|170|9.1|6.8|7.0
Leite Desnatado|100|4.5|3.0|1.0
Leite em pó|100|38.0|27.0|27.0
Leite Integral|100|5.0|3.0|3.0
Leite Po|100|55.0|35.0|0.0
Leucina|100|0.0|100.0|0.0
Linhaca|100|0.0|20.0|40.0
Maca|100|16.6|0.2|0.2
Maionese LIght|100|8.3|0.0|24.2
Maisena|30|22.0|2.4|3.6
Malto|100|92.0|0.0|0.0
Mamao|100|10.4|0.5|0.1
Mignon|100|0.0|22.5|25.5
Novo Pao Integral|100|28.0|17.4|4.6
Nozes|100|13.0|15.0|67.0
Nutella|100|57.0|7.0|30.0
Nutella|100|57.0|7.0|30.0
Ovo|100|0.0|13.3|9.5
Ovo frito|100|0.0|15.6|18.6
Ovo Mexido|100|2.2|11.1|12.2
Pão de Forma Light|100|40.0|10.8|4.0
Pao de Forma Integral|50|24.0|4.8|1.0
Pão Frances|100|58.6|8.0|0.0
Pasta de Amendoim|100|17.0|29.0|55.0
Peito de Frango Grelhado|100|0.0|31.0|3.6
Peito de Frango [Cru]|100|0.0|21.5|3.0
Peito de Peru|100|0.0|24.0|2.0
Pera|100|14.0|0.6|0.1
Queijo Minas|100|3.6|21.2|24.6
Queijo Canastra|30|0.9|8.2|8.5
Rap10|50|20.0|3.4|3.2
Requeijao Aviacao|100|0.0|11.3|19.6
Requeijão Light|100|3.0|10.0|13.0
Tapioca|100|66.0|2.0|0.0
Torrada|30|21.2|5.6|3.2
Vagem Cozida|100|6.9|3.2|2.5
Vigor|100|15.0|4.9|7.5
Vigor Integral|100|3.9|5.9|2.2
Whey|100|2.0|88.0|0.8
Whey Growth|100|10.0|77.0|6.3
Yorgus|100|6.0|14.0|0.0
Leite Sem Lactose|100|4.5|3.1|1.2
Gelo|100|0.0|0.0|0.0
Café|100|0.0|0.0|0.0
Pão sem Glúten|100|16.0|3.0|0.5
Mix Sementes|100|4.3|4.9|11.0
Salada|100|0.0|0.0|0.0
Legumes Cozidos|100|6.0|0.4|0.8
Banana|100|26.0|1.3|0.1
Ervilha|100|13.4|4.6|0.4
Bife de Patinho|100|0.0|35.9|7.3
Semente de Chia|100|42.1|16.5|30.7
"""


def foods_by_name() -> dict[str, dict]:
    foods: dict[str, dict] = {}
    for name, grams, carbs, protein, fats in csv.reader(
        StringIO(FOOD_DATA.strip()), delimiter="|"
    ):
        serving_grams = float(grams)
        factor = 100 / serving_grams
        food = {
            "name": name,
            "carbs_per_100g": round(float(carbs) * factor, 2),
            "protein_per_100g": round(float(protein) * factor, 2),
            "fats_per_100g": round(float(fats) * factor, 2),
        }
        previous = foods.get(name)
        if previous and previous != food:
            print(f"{name}: duplicate with different macros; using the last row.")
        foods[name] = food
    return foods


def main() -> int:
    try:
        existing_names = {food["name"] for food in client.get_foods(limit=500)}
    except ApiError as error:
        print(f"Could not load existing foods: {error.message}", file=sys.stderr)
        return 1

    created = 0
    skipped_existing = 0
    skipped_invalid = 0
    failed = 0

    for food in foods_by_name().values():
        macros = (
            food["carbs_per_100g"]
            + food["protein_per_100g"]
            + food["fats_per_100g"]
        )
        if macros > 100:
            print(
                f"Skipping {food['name']}: normalized macros sum to "
                f"{macros:.2f} g per 100 g."
            )
            skipped_invalid += 1
            continue

        if food["name"] in existing_names:
            skipped_existing += 1
            continue

        try:
            client.create_food(food)
        except ApiError as error:
            print(f"Could not add {food['name']}: {error.message}", file=sys.stderr)
            failed += 1
            continue

        existing_names.add(food["name"])
        created += 1

    print(
        f"Import complete: {created} created, {skipped_existing} already existed, "
        f"{skipped_invalid} invalid rows skipped, {failed} failed."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

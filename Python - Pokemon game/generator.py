from __future__ import annotations

from pathlib import Path
from typing import List, Optional

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

from pokemon import Pokemon

DATA_FILE = Path(__file__).with_name("Pokemon database.xlsx")
EXPECTED_COLUMNS = (
    "Name",
    "Type 1",
    "Type 2",
    "HP",
    "Attack",
    "Defense",
    "Sp.Attack",
    "Sp.Defense",
    "Speed",
)


def _load_database():
    if pd is None:
        raise ModuleNotFoundError(
            "pandas is required to read the Pokemon database spreadsheet."
        )

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Database file not found at {DATA_FILE}.")

    df = pd.read_excel(DATA_FILE)
    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Database is missing expected columns: {', '.join(missing)}")
    return df


def _extract_types(record) -> tuple[str, ...]:
    types: List[str] = []
    for column in ("Type 1", "Type 2"):
        value = record.get(column)
        if isinstance(value, str):
            value = value.strip().lower()
            if value:
                types.append(value)
    if not types:
        raise ValueError(f"Pokemon '{record.get('Name', 'Unknown')}' is missing type information")
    return tuple(types)


def _row_to_pokemon(record, *, level: Optional[int] = None, gender: Optional[int] = None) -> Pokemon:
    try:
        hp = int(record["HP"])
        attack = int(record["Attack"])
        defense = int(record["Defense"])
        sp_attack = int(record["Sp.Attack"])
        sp_defense = int(record["Sp.Defense"])
        speed = int(record["Speed"])
    except KeyError as exc:
        raise ValueError(f"Missing stat column in database: {exc}") from exc

    name = str(record["Name"])

    stats = (attack, speed, sp_attack, defense, sp_defense, hp, hp)
    return Pokemon(
        name=name,
        gender=gender if gender is not None else 2,
        stats=stats,
        level=level if level is not None else 50,
        moves=[],
        element=_extract_types(record),
    )


def _lookup_record(database, name: str):
    normalised = name.strip().lower()
    matches = database[database["Name"].str.lower() == normalised]
    if matches.empty:
        raise ValueError(f"Pokemon named '{name}' was not found in the database")
    return matches.iloc[0]


def _resolve_entry(entry, database, used_names: set[str]) -> Optional[Pokemon]:
    if isinstance(entry, Pokemon):
        used_names.add(entry.name.lower())
        return entry

    if isinstance(entry, str):
        record = _lookup_record(database, entry)
        pokemon = _row_to_pokemon(record)
        used_names.add(pokemon.name.lower())
        return pokemon

    return None


def _fill_random_slots(team: List[Optional[Pokemon]], database, used_names: set[str]) -> None:
    available = database[~database["Name"].str.lower().isin(used_names)]
    for index, entry in enumerate(team):
        if entry is None:
            if available.empty:
                raise ValueError("Not enough unique Pokemon remain to fill the team")
            record = available.sample(1).iloc[0]
            pokemon = _row_to_pokemon(record)
            team[index] = pokemon
            used_names.add(pokemon.name.lower())
            available = available[~available["Name"].str.lower().isin(used_names)]


def generate_team(P1=None, P2=None, P3=None, P4=None, P5=None, P6=None, random=None) -> List[Pokemon]:
    """Create a list of Pokemon instances sourced from the database."""

    database = _load_database()
    slots = [P1, P2, P3, P4, P5, P6]
    used_names: set[str] = set()
    team: List[Optional[Pokemon]] = []

    for entry in slots:
        pokemon = _resolve_entry(entry, database, used_names)
        team.append(pokemon)

    if random:
        _fill_random_slots(team, database, used_names)

    missing_indices = [index for index, pokemon in enumerate(team) if pokemon is None]
    if missing_indices:
        missing_slots = ", ".join(str(index + 1) for index in missing_indices)
        raise ValueError(f"Team slots {missing_slots} are unfilled. Provide names or use random=True.")

    return [pokemon for pokemon in team if pokemon is not None]

    

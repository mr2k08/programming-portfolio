NATURES = {
    'Adamant': {
        'increase': 'atk',
        'decrease': 'sp_atk',
        'description': 'Increases Attack, Decreases Sp. Attack'
    },
    'Bold': {
        'increase': 'defense',
        'decrease': 'atk',
        'description': 'Increases Defense, Decreases Attack'
    },
    'Modest': {
        'increase': 'sp_atk',
        'decrease': 'atk',
        'description': 'Increases Sp. Attack, Decreases Attack'
    },
    'Calm': {
        'increase': 'sp_def',
        'decrease': 'atk',
        'description': 'Increases Sp. Defense, Decreases Attack'
    },
    'Timid': {
        'increase': 'spd',
        'decrease': 'atk',
        'description': 'Increases Speed, Decreases Attack'
    },
    'Jolly': {
        'increase': 'spd',
        'decrease': 'sp_atk',
        'description': 'Increases Speed, Decreases Sp. Attack'
    },
    'Careful': {
        'increase': 'sp_def',
        'decrease': 'sp_atk',
        'description': 'Increases Sp. Defense, Decreases Sp. Attack'
    }
}

class Pokemon:
    def __init__(self,name:str, gender: int,stats: tuple, level: int, moves: list, element: tuple, special_trait= None,status=None,item=None, temper=None):
        self.name = name
        self.gender= gender
        self.temper=temper
        self.element=element
        self.atk, self.spd, self.sp_atk ,self.defense ,self.sp_def, self.hp,self.max_hp = stats
        self.level=level
        self.moves=moves
        self.status=status
        self.special_trait=special_trait
        self.nature_effect = None

        self.base_stats = {
            'atk': self.atk,
            'defense': self.defense,
            'sp_atk': self.sp_atk,
            'sp_def': self.sp_def,
            'spd': self.spd,
            'hp': self.hp,
            'max_hp': self.max_hp
        }

        self._apply_nature()

    def _apply_nature(self):
        if not self.temper:
            return

        nature = NATURES.get(self.temper)
        if not nature:
            print(f"Warning: Unknown nature '{self.temper}' for {self.name}")
            return

        self.nature_effect = nature
        increase = nature['increase']
        decrease = nature['decrease']

        if increase == decrease:
            return

        self._modify_stat_by_multiplier(increase, 1.1)
        self._modify_stat_by_multiplier(decrease, 0.9)

    def _modify_stat_by_multiplier(self, stat_name: str, multiplier: float) -> None:
        if not hasattr(self, stat_name):
            return

        base_value = self.base_stats.get(stat_name, getattr(self, stat_name))
        modified = max(1, int(round(base_value * multiplier)))
        setattr(self, stat_name, modified)

    def nature_summary(self) -> str:
        if not self.temper or not self.nature_effect:
            return "Neutral"

        increase = self.nature_effect['increase']
        decrease = self.nature_effect['decrease']

        if increase == decrease:
            return f"{self.temper} (neutral)"

        inc_label = self._format_stat_label(increase)
        dec_label = self._format_stat_label(decrease)
        return f"{self.temper} (+{inc_label} / -{dec_label})"

    @staticmethod
    def _format_stat_label(stat_key: str) -> str:
        label_map = {
            'atk': 'Attack',
            'defense': 'Defense',
            'sp_atk': 'Sp. Attack',
            'sp_def': 'Sp. Defense',
            'spd': 'Speed'
        }
        return label_map.get(stat_key, stat_key.replace('_', ' ').title())

class Attack:
    def __init__(self, name, element, power:int, compatible_elements: tuple, PP: int, acc: int,critical: int, type: str):
        self.name=name
        self.element=element
        self.power=power
        self.compatible_elements=compatible_elements
        self.PP=PP
        self.critical=critical
        self.acc=acc
        self.type=type

class SpecialMoves:
    def __init__(self,name: str,effect: str, effect_target: int, effect_scale: int, acc: int):
        self.name=name
        self.effect=effect
        self.effect_target=effect_target
        self.effect_scale=effect_scale
        self.acc=acc

def critical(user: Pokemon, move: Attack):
    from random import randint
    return randint(1,100)<=move.critical

def miss(user: Pokemon,move):
    from random import randint
    if type(move)==Attack:
        return randint(1,100)> (move.acc if user.status!='drowsy' else move.acc+20)
    else:
        return False

class Item:
    def __init__(self, name: str, effect: str, effect_scale: int):
        self.name = name
        self.effect = effect
        self.effect_scale = effect_scale

class Bag:
    def __init__(self,items: list):
        self.items=items

def use_item(item: Item, pokemon: Pokemon) -> bool:
    if item.effect == "heal":
        if pokemon.hp == pokemon.max_hp:
            print(f"\n{pokemon.name}'s HP is already full!")
            return False
        old_hp = pokemon.hp
        pokemon.hp = min(pokemon.hp + item.effect_scale, pokemon.max_hp)
        healed = pokemon.hp - old_hp

        print(f"\n{pokemon.name} recovered {healed} HP!")
        return True
    elif item.effect in ["atk", "def", "spd"]:
        if item.effect == "atk":
            pokemon.atk += item.effect_scale
            pokemon.sp_atk += item.effect_scale
            print(f"\n{pokemon.name}'s Attack and Sp. Attack rose!")
        elif item.effect == "def":
            pokemon.defense += item.effect_scale
            pokemon.sp_def += item.effect_scale
            print(f"\n{pokemon.name}'s Defense and Sp. Defense rose!")
        elif item.effect == "spd":
            pokemon.spd += item.effect_scale
            print(f"\n{pokemon.name}'s Speed rose!")
        return True
    return False

def cast_buff_nerf(move: SpecialMoves, user: Pokemon, target: Pokemon):
    stat_map = {
        'atk': ['atk', 'sp_atk'],
        'def': ['defense', 'sp_def'],
        'spd': ['spd']
    }

    affected_pokemon = user if move.effect_target else target
    modifier = 1 if move.effect_target else -1

    if move.effect in stat_map:
        print(f"\n{affected_pokemon.name}'s stats changed:")
        for stat in stat_map[move.effect]:
            old_value = getattr(affected_pokemon, stat)
            new_value = old_value + (move.effect_scale * modifier)
            setattr(affected_pokemon, stat, new_value)

            change = "↑" if modifier > 0 else "↓"
            print(f"{stat.upper()}: {old_value} {change} {new_value}")

TYPE_CHART = {
    "normal": {
        "rock": 0.5,
        "ghost": 0,
        "steel": 0.5
    },
    "fire": {
        "fire": 0.5,
        "water": 0.5,
        "grass": 2,
        "ice": 2,
        "bug": 2,
        "rock": 0.5,
        "dragon": 0.5,
        "steel": 2
    },
    "water": {
        "fire": 2,
        "water": 0.5,
        "grass": 0.5,
        "ground": 2,
        "rock": 2,
        "dragon": 0.5
    },
    "electric": {
        "water": 2,
        "electric": 0.5,
        "grass": 0.5,
        "ground": 0,
        "flying": 2,
        "dragon": 0.5
    },
    "grass": {
        "fire": 0.5,
        "water": 2,
        "grass": 0.5,
        "poison": 0.5,
        "ground": 2,
        "flying": 0.5,
        "bug": 0.5,
        "rock": 2,
        "dragon": 0.5,
        "steel": 0.5
    },
    "ice": {
        "fire": 0.5,
        "water": 0.5,
        "grass": 2,
        "ice": 0.5,
        "ground": 2,
        "flying": 2,
        "dragon": 2,
        "steel": 0.5
    },
    "fighting": {
        "normal": 2,
        "ice": 2,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 0.5,
        "bug": 0.5,
        "rock": 2,
        "ghost": 0,
        "dark": 2,
        "steel": 2
    },
    "poison": {
        "grass": 2,
        "poison": 0.5,
        "ground": 0.5,
        "rock": 0.5,
        "ghost": 0.5,
        "steel": 0
    },
    "ground": {
        "fire": 2,
        "electric": 2,
        "grass": 0.5,
        "poison": 2,
        "flying": 0,
        "bug": 0.5,
        "rock": 2,
        "steel": 2
    },
    "flying": {
        "electric": 0.5,
        "grass": 2,
        "fighting": 2,
        "bug": 2,
        "rock": 0.5,
        "steel": 0.5
    },
    "psychic": {
        "fighting": 2,
        "poison": 2,
        "psychic": 0.5,
        "dark": 0,
        "steel": 0.5
    },
    "bug": {
        "fire": 0.5,
        "grass": 2,
        "fighting": 0.5,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 2,
        "ghost": 0.5,
        "dark": 2,
        "steel": 0.5
    },
    "rock": {
        "fire": 2,
        "ice": 2,
        "fighting": 0.5,
        "ground": 0.5,
        "flying": 2,
        "bug": 2,
        "steel": 0.5
    },
    "ghost": {
        "normal": 0,
        "psychic": 2,
        "ghost": 2,
        "dark": 0.5
    },
    "dragon": {
        "dragon": 2,
        "steel": 0.5
    },
    "dark": {
        "fighting": 0.5,
        "psychic": 2,
        "ghost": 2,
        "dark": 0.5
    },
    "steel": {
        "fire": 0.5,
        "water": 0.5,
        "electric": 0.5,
        "ice": 2,
        "rock": 2,
        "steel": 0.5
    }
}

def calculate_type_effectiveness(move_type: str, defender_types: tuple) -> float:
    """Calculate type effectiveness multiplier"""
    multiplier = 1.0
    for def_type in defender_types:
        if move_type in TYPE_CHART and def_type in TYPE_CHART[move_type]:
            multiplier *= TYPE_CHART[move_type][def_type]
    return multiplier

def get_stab_bonus(attacker_types: tuple, move_type: str) -> float:
    """Calculate Same Type Attack Bonus"""
    return 1.5 if move_type in attacker_types else 1.0

def attack(attacker: Pokemon, defender: Pokemon, move):
    if move.PP <= 0:
        return {
            'hit': False,
            'reason': 'no_pp',
            'type_effectiveness': 1.0,
            'critical': False,
            'damage': 0
        }

    if miss(attacker, move):
        move.PP -= 1
        return {
            'hit': False,
            'reason': 'miss',
            'type_effectiveness': 1.0,
            'critical': False,
            'damage': 0
        }

    stab = get_stab_bonus(attacker.element, move.element)
    type_effect = calculate_type_effectiveness(move.element, defender.element)

    if type_effect == 0:
        print('it has no effect')
    elif type_effect > 1:
        print('super effective!')
    elif type_effect < 1:
        print('not very effective...')
    else:
        print('effective!')

    if move.type == "physical":
        attack_stat = max(1, attacker.atk)
        defense_stat = max(1, defender.defense)
    else:
        attack_stat = max(1, attacker.sp_atk)
        defense_stat = max(1, defender.sp_def)

    base_damage = (attack_stat / defense_stat) * move.power + 10
    level = max(1, getattr(attacker, 'level', 1))
    level_modifier = ((2 * level) / 5 + 2) / 50
    base_damage = base_damage * level_modifier + 2

    damage = base_damage * stab * type_effect

    is_critical = critical(attacker, move)
    if is_critical:
        damage *= 2

    from random import randint
    damage *= randint(85, 100) / 100

    if type_effect == 0:
        final_damage = 0
    else:
        final_damage = max(1, int(damage)) + randint(1,15)

    defender.hp = max(0, defender.hp - final_damage)
    move.PP -= 1

    return {
        'hit': True,
        'reason': 'hit',
        'type_effectiveness': type_effect,
        'critical': is_critical,
        'damage': final_damage
    }

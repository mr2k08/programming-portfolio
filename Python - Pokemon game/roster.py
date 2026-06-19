"""Default move, Pokémon, and player setup for the battle simulator."""

from pokemon import Attack, SpecialMoves, Pokemon, Item, Bag
from Player import Player

def create_players():
    """Instantiate the default teams, bags, and players."""
    # Moves
    precipice_blades = Attack("Precipice Blades", "ground", 120, ("ground",), 5, 85, 10, "physical")
    heat_crash = Attack("Heat Crash", "fire", 100, ("fire",), 10, 100, 10, "physical")
    dragon_claw = Attack("Dragon Claw", "dragon", 80, ("dragon",), 15, 100, 15, "physical")
    solar_beam = Attack("Solar Beam", "grass", 120, ("grass",), 10, 100, 10, "special")
    dark_pulse = Attack("Dark Pulse", "dark", 80, ("dark",), 15, 100, 10, "special")
    giga_impact = Attack("Giga Impact", "normal", 150, ("normal",), 5, 90, 10, "physical")
    tera_blast = Attack("Tera Blast", "normal", 120, ("normal",), 10, 100, 10, "special")
    ice_beam = Attack("Ice Beam", "ice", 90, ("ice", "water"), 10, 100, 10, "special")
    aeroblast = Attack("Aeroblast", "flying", 100, ("flying",), 5, 95, 20, "special")
    thunder_wave = SpecialMoves("Thunder Wave", "spd", -1, 20, 90)
    reflect = SpecialMoves("Reflect", "def", 1, 20, 100)
    hyper_beam = Attack("Hyper Beam", "normal", 150, ("normal",), 5, 90, 10, "special")
    earthquake = Attack("Earthquake", "ground", 100, ("ground",), 10, 100, 10, "physical")
    high_horsepower = Attack("High Horsepower", "ground", 95, ("ground",), 10, 95, 10, "physical")
    rest = SpecialMoves("Rest", "hp", 1, 10, 100)
    facade = Attack("Facade", "normal", 70, ("normal",), 20, 100, 10, "physical")
    swords_dance = SpecialMoves("Swords Dance", "atk", 2, 20, 100)
    extreme_speed = Attack("Extreme Speed", "normal", 80, ("normal",), 5, 100, 10, "physical")
    shadow_claw = Attack("Shadow Claw", "ghost", 70, ("ghost",), 15, 100, 20, "physical")
    recover = SpecialMoves("Recover", "hp", 1, 10, 100)
    draco_meteor = Attack("Draco Meteor", "dragon", 130, ("dragon",), 5, 90, 10, "special")
    flash_cannon = Attack("Flash Cannon", "steel", 80, ("steel",), 10, 100, 10, "special")
    earth_power = Attack("Earth Power", "ground", 90, ("ground",), 10, 100, 10, "special")
    dynamax_cannon = Attack("Dynamax Cannon", "dragon", 140, ("dragon",), 5, 100, 10, "special")
    sludge_bomb = Attack("Sludge Bomb", "poison", 90, ("poison",), 10, 100, 10, "special")
    flamethrower = Attack("Flamethrower", "fire", 90, ("fire",), 15, 100, 10, "special")
    shadow_ball = Attack("Shadow Ball", "ghost", 80, ("ghost",), 15, 100, 10, "special")
    focus_blast = Attack("Focus Blast", "fighting", 120, ("fighting",), 5, 70, 10, "special")
    destiny_bond = SpecialMoves("Destiny Bond", "self", 0, 5, 100)
    growth = SpecialMoves("Growth", "atk", 1, 20, 100)
    giga_drain = Attack("Giga Drain", "grass", 75, ("grass",), 10, 100, 10, "special")
    dragon_dance = SpecialMoves("Dragon Dance", "atk", 1, 20, 100)
    dragon_ascent = Attack("Dragon Ascent", "flying", 120, ("flying",), 5, 100, 10, "physical")
    psycho_boost = Attack("Psycho Boost", "psychic", 140, ("psychic",), 5, 90, 10, "special")
    thunderbolt = Attack("Thunderbolt", "electric", 90, ("electric",), 15, 100, 10, "special")
    behemoth_blade = Attack("Behemoth Blade", "steel", 150, ("steel",), 5, 100, 10, "physical")
    play_rough = Attack("Play Rough", "fairy", 90, ("fairy",), 10, 90, 10, "physical")
    sacred_sword = Attack("Sacred Sword", "fighting", 90, ("fighting",), 15, 100, 10, "physical")
    shadow_force = Attack("Shadow Force", "ghost", 120, ("ghost", "dragon"), 5, 100, 1, "physical")
    dragon_claw = Attack("Dragon Claw", "dragon", 80, ("dragon",), 15, 100, 1, "physical")
    protect = SpecialMoves("Protect", "block all damage this turn", 0, 0, 100)
    will_o_wisp = SpecialMoves("Will-O-Wisp", "burn", 1, 0, 85)
    double_iron_bash = Attack("Double Iron Bash", "steel", 60, ("steel",), 5, 100, 1, "physical")
    thunder_punch = Attack("Thunder Punch", "electric", 75, ("steel", "electric"), 15, 100, 1, "physical")
    toxic = SpecialMoves("Toxic", "badly poison", 1, 0, 90)
    protect_metal = SpecialMoves("Protect", "block all damage this turn", 0, 0, 100)
    earthquake = Attack("Earthquake", "ground", 100, ("ground", "normal"), 10, 100, 1, "physical")
    high_horsepower = Attack("High Horsepower", "ground", 95, ("ground", "normal"), 10, 95, 1, "physical")
    facade = Attack("Facade", "normal", 70, ("normal",), 20, 100, 1, "physical")

    # Pokémon
    darkrai = Pokemon(
        "Darkrai",
        1,
        (90, 105, 115, 80, 85, 344, 344),
        75,
        [dark_pulse, ice_beam, giga_impact, tera_blast],
        ("dark"),
        special_trait="Bad Dreams",
        temper="Timid",
    )
    lugia = Pokemon(
        "Lugia",
        2,
        (90, 110, 90, 130, 154, 416, 416),
        75,
        [aeroblast, thunder_wave, reflect, hyper_beam],
        ("psychic", "flying"),
        special_trait="Pressure",
        temper="Bold",
    )
    groudon = Pokemon(
        "Groudon",
        0,
        (150, 90, 100, 140, 90, 414, 414),
        75,
        [precipice_blades, heat_crash, dragon_claw, solar_beam],
        ("ground",),
        special_trait="Drought",
        temper="Adamant",
    )
    melmetal = Pokemon(
    "Melmetal",
    0,
    (143, 34, 65, 143, 90, 874, 874),  # atk, spd, sp_atk, defense, sp_def, hp, max_hp
    70,
    [double_iron_bash, thunder_punch, protect, toxic],
    ("steel",),
    special_trait="Iron Fist",
    temper="Adamant"
    )

    giratina = Pokemon(
    "Giratina",
    0,
    (100, 90, 100, 120, 120, 540, 540),  # atk, spd, sp_atk, defense, sp_def, hp, max_hp
    70,
    [shadow_force, dragon_claw, will_o_wisp, protect],
    ("ghost", "dragon"),
    special_trait="Pressure",
    temper="Bold"
    )


    snorlax = Pokemon(
        "Snorlax",
        0,
        (110, 30, 65, 65, 110, 524, 524),
        75,
        [earthquake, high_horsepower, rest, facade],
        ("normal",),
        special_trait="Thick Fat",
        temper="Brave",
    )
    arceus = Pokemon(
        "Arceus",
        2,
        (120, 120, 120, 120, 120, 480, 480),
        75,
        [swords_dance, extreme_speed, shadow_claw, recover],
        ("normal",),
        special_trait="Multitype",
        temper="Serious",
    )
    dialga = Pokemon(
        "Dialga",
        2,
        (100, 90, 150, 120, 100, 420, 420),
        75,
        [draco_meteor, flash_cannon, earth_power, ice_beam],
        ("steel", "dragon"),
        special_trait="Pressure",
        temper="Modest",
    )
    rayquaza = Pokemon(
        "Rayquaza",
        0,
        (105, 95, 150, 90, 90, 414, 414),
        75,
        [dragon_dance, dragon_ascent, earthquake, extreme_speed],
        ("dragon", "flying"),
        special_trait="Air Lock",
        temper="Adamant",
    )
    venusaur = Pokemon(
        "Venusaur",
        1,
        (82, 80, 100, 83, 100, 364, 364),
        75,
        [growth, sludge_bomb, giga_drain, earth_power],
        ("grass", "poison"),
        special_trait="Overgrow",
        temper="Modest",
    )
    gengar = Pokemon(
        "Gengar",
        0,
        (65, 110, 130, 60, 75, 324, 324),
        75,
        [shadow_ball, sludge_bomb, focus_blast, destiny_bond],
        ("ghost", "poison"),
        special_trait="Levitate",
        temper="Timid",
    )
    zacian = Pokemon(
        "Zacian",
        2,
        (145, 148, 100, 115, 115, 384, 384),
        75,
        [behemoth_blade, play_rough, sacred_sword, swords_dance],
        ("fairy",),
        special_trait="Intrepid Sword",
        temper="Jolly",
    )
    eternatus = Pokemon(
        "Eternatus",
        2,
        (195, 130, 145, 95, 95, 424, 424),
        75,
        [dynamax_cannon, sludge_bomb, flamethrower, recover],
        ("poison", "dragon"),
        special_trait="Pressure",
        temper="Modest",
    )
    deoxys_attack = Pokemon(
        "Deoxys-A",
        2,
        (120, 150, 150, 95, 75, 312, 312),
        75,
        [psycho_boost, ice_beam, thunderbolt, extreme_speed],
        ("psychic",),
        special_trait="Pressure",
        temper="Rash",
    )

    team1 = [darkrai, lugia, groudon, arceus, dialga, snorlax]
    team2 = [giratina, melmetal, gengar, zacian, eternatus, deoxys_attack]

    # Items and bags
    potion = Item("Potion", "heal", 50)
    super_potion = Item("Super Potion", "heal", 100)
    hyper_potion = Item("Hyper Potion", "heal", 200)
    x_attack = Item("X Attack", "atk", 20)
    x_defense = Item("X Defense", "def", 20)
    x_speed = Item("X Speed", "spd", 20)

    bag1 = Bag([hyper_potion, x_attack, x_speed])
    bag2 = Bag([super_potion, x_defense, potion])

    player1 = Player("Marc htn", team1, bag1)
    player2 = Player("Marc twink sub 5", team2, bag2)

    return player1, player2

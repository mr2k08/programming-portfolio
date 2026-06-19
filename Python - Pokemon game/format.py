from pokemon import Attack
from os import system
def clear_terminal():
    _ = system('clear')

def print_battle_status(player1, player2, current_player):
    print("\n" + "="*70)
    print(f"{'Trainer 1' if current_player == player1 else 'Trainer 2'}'s turn!")
    print(f"{player1.current_pokemon.name:^25} VS {player2.current_pokemon.name:^25}")
    print(f"{player1.current_pokemon.nature_summary():^25} VS {player2.current_pokemon.nature_summary():^25}")
    print(f"HP: {player1.current_pokemon.hp:>3}/{player1.current_pokemon.max_hp:<3}{' '*17}HP: {player2.current_pokemon.hp:>3}/{player2.current_pokemon.max_hp:<3}")
    print("="*70 + "\n")

def print_move_options(pokemon):
    print("\nMoves:")
    print("-"*70)
    for i, move in enumerate(pokemon.moves, 1):
        if isinstance(move, Attack):
            print(f"{i}. {move.name:<15} | Power: {move.power:<3} | PP: {move.PP:<2} | Type: {move.element:<8} | {move.type}")
        else:
            effect_type = "Raises" if move.effect_target == 1 else "Lowers"
            target = "self" if move.effect_target == 1 else "opponent"
            print(f"{i}. {move.name:<15} | {effect_type} {move.effect} by {move.effect_scale} ({target}) | Accuracy: {move.acc}")
    print("-"*70)

def print_bag_options(bag):
    print("\nBag:")
    print("-"*50)
    for i, item in enumerate(bag.items, 1):
        print(f"{i}. {item.name:<15} | Effect: {item.effect:<4} | Power: {item.effect_scale}")
    print("-"*50)

def print_battle_menu():
    print("\nWhat would you like to do?")
    print("1. Fight")
    print("2. Bag")
    print("3. Switch Pokemon")
    print("4. Run")

def print_switch_options(player):
    print("\nSwitch to:")
    print("-"*50)
    for i, pokemon in enumerate(player.team, 1):
        if pokemon != player.current_pokemon and pokemon.hp > 0:
            print(f"{i}. {pokemon.name:<15} | HP: {pokemon.hp}/{pokemon.max_hp} | Types: {', '.join(pokemon.element)}")
    print("-"*50)

def print_warning(type):
    match type:
        case 'p':
            print("\nCan't switch to that Pokemon!")
        case 'ip':
            print("\nInvalid Pokemon number!")
        case 'ic':
            print("\nInvalid choice!")
        case 'ce':
            print("\nCan't escape from a trainer battle!")

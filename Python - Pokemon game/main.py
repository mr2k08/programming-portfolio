from os import chdir
from time import sleep

from format import *
from pokemon import *
from roster import create_players


lives_1, lives_2 = 6, 6
player1, player2 = create_players()
current_player = player1 if player1.current_pokemon.spd >= player2.current_pokemon.spd else player2

# Update the main game loop
while lives_1 and lives_2:
    clear_terminal()
    
    # Check if current Pokemon has fainted
    if current_player.current_pokemon.hp <= 0:
        print(f"\n{current_player.current_pokemon.name} has fainted!")
        if current_player == player1:
            lives_1 -= 1
        else:
            lives_2 -= 1
            
        if lives_1 <= 0:
            clear_terminal()
            print(f"Trainer {player2.name} wins!")
            break
        elif lives_2 <= 0:
            clear_terminal()
            print(f"{player1.name} 1 wins!")
            break
            
        # Force switch to a healthy Pokemon
        healthy_pokemon = lives_1 if current_player == player1 else lives_2
        if healthy_pokemon:
            print("\nChoose your next Pokemon:")
            for i, pokemon in enumerate(current_player.team, 1):
                if pokemon.hp > 0:
                    print(f"{i}. {pokemon.name} (HP: {pokemon.hp}/{pokemon.max_hp})")
            
            while True:
                try:
                    switch_choice = input("\nChoose a Pokemon (1-6): ")
                    switch_index = int(switch_choice) - 1
                    if 0 <= switch_index < len(current_player.team):
                        new_pokemon = current_player.team[switch_index]
                        if new_pokemon.hp > 0:
                            current_player.current_pokemon = new_pokemon
                            print(f"\n{current_player.current_pokemon.name}, I choose you!")
                            sleep(1)
                            break
                    print("\nInvalid choice! Choose a healthy Pokemon.")
                except ValueError:
                    print("\nInvalid input! Enter a number.")
            continue

    print_battle_status(player1, player2, current_player)
    print_battle_menu()
    
    choice = input(f"\nTrainer {current_player.name}, enter your choice (1-4): ")
    
    if choice == "1":
        print_move_options(current_player.current_pokemon)
        move_choice = input("\nChoose a move (1-4) or 'b' to go back: ")
        if move_choice.lower() == 'b':
            continue
            
        try:
            move_index = int(move_choice) - 1
            if 0 <= move_index < len(current_player.current_pokemon.moves):
                selected_move = current_player.current_pokemon.moves[move_index]
                target = player2.current_pokemon if current_player == player1 else player1.current_pokemon
                
                if isinstance(selected_move, Attack):
                    # Handle regular attack
                    if selected_move.PP <= 0:
                        print("\nNo PP left for this move!")
                        sleep(1)
                        continue
                        
                    result = attack(current_player.current_pokemon, target, selected_move)
                    if not result['hit']:
                        if result['reason'] == 'miss':
                            print(f"\n{current_player.current_pokemon.name}'s attack missed!")
                        elif result['reason'] == 'no_pp':
                            print(f"\n{selected_move.name} is out of PP!")
                        else:
                            print(f"\n{current_player.current_pokemon.name}'s move failed!")
                    else:
                        print(f"\n{current_player.current_pokemon.name} used {selected_move.name}!")
                        if result['critical']:
                            print("A critical hit!")
                        
                    # Prevent negative HP
                    if target.hp < 0:
                        target.hp = 0
                    
                else:  # Handle special moves (SpecialMoves)
                    cast_buff_nerf(selected_move, current_player.current_pokemon, target)
                    print(f"\n{current_player.current_pokemon.name} used {selected_move.name}!")
                
                sleep(1.5)
                current_player = player2 if current_player == player1 else player1
                
            else:
                print("\nInvalid move number!")
                sleep(1)
                
        except ValueError:
            print("\nInvalid choice!")
            sleep(1)
    
    elif choice == "2":
        print_bag_options(current_player.bag)
        item_choice = input("\nChoose an item (1-3) or 'b' to go back: ")
        if item_choice.lower() == 'b':
            continue
            
        try:
            item_index = int(item_choice) - 1
            if 0 <= item_index < len(current_player.bag.items):
                selected_item = current_player.bag.items[item_index]
                
                # Ask which Pokémon to use the item on
                print("\nUse on which Pokemon?")
                for i, pokemon in enumerate(current_player.team, 1):
                    print(f"{i}. {pokemon.name} (HP: {pokemon.hp}/{pokemon.max_hp})")
                
                target_choice = input("\nChoose a Pokemon (1-6) or 'b' to go back: ")
                if target_choice.lower() == 'b':
                    continue
                
                try:
                    target_index = int(target_choice) - 1
                    if 0 <= target_index < len(current_player.team):
                        target_pokemon = current_player.team[target_index]
                        
                        if target_pokemon.hp <= 0:
                            print(f"\n{target_pokemon.name} is fainted and cannot use items!")
                            sleep(1)
                            continue
                            
                        if use_item(selected_item, target_pokemon):
                            # Remove used item from bag
                            current_player.bag.items.pop(item_index)
                            sleep(1)
                            current_player = player2 if current_player == player1 else player1
                        else:
                            sleep(1)
                            continue
                    else:
                        print("\nInvalid Pokemon number!")
                        sleep(1)
                except ValueError:
                    print("\nInvalid choice!")
                    sleep(1)
            else:
                print("\nInvalid item number!")
                sleep(1)
        except ValueError:
            print("\nInvalid choice!")
            sleep(1)
    
    elif choice == "3":
        print_switch_options(current_player)
        switch_choice = input("\nChoose a Pokemon (1-6) or 'b' to go back: ")
        if switch_choice.lower() == 'b':
            continue
        try:
            switch_index = int(switch_choice) - 1
            if 0 <= switch_index < len(current_player.team):
                new_pokemon = current_player.team[switch_index]
                if new_pokemon != current_player.current_pokemon and new_pokemon.hp > 0:
                    current_player.current_pokemon = new_pokemon
                    print(f"\n{current_player.current_pokemon.name}, I choose you!")
                    sleep(1)
                    current_player = player2 if current_player == player1 else player1
                else:
                    print_warning('p')
                    sleep(1)
            else:
                print_warning('ip')
                sleep(1)
        except ValueError:
            print_warning('ic')
            sleep(1)

    elif choice == "4":
        print_warning('ce')
        sleep(1)
    
# Game over message (outside the main loop)
print("\nGame Over!")
sleep(2)














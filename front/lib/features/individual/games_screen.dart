import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';
import 'package:flutter_application_1/features/games/breathing_bubble.dart';
import 'package:flutter_application_1/features/games/color_match.dart'; 
import 'package:flutter_application_1/features/games/emotion_garden.dart';
import 'package:flutter_application_1/features/games/memory_card.dart';
import 'package:flutter_application_1/features/games/connect_paths.dart';
import 'package:flutter_application_1/features/games/catch_drops.dart';
import 'community/communitygames.dart'; // Import the new Community Games screen

// Helper class to store game data cleanly
class GameItem {
  final String title;
  final String description;
  final String tag;
  final Widget screen;

  GameItem({
    required this.title, 
    required this.description, 
    required this.tag, 
    required this.screen
  });
}

class GamesScreen extends StatefulWidget {
  @override
  _GamesScreenState createState() => _GamesScreenState();
}

class _GamesScreenState extends State<GamesScreen> {
  // 1. Key to track the "All Games" section for scrolling
  final GlobalKey _allGamesKey = GlobalKey();

  // 2. Filter State
  String _selectedFilter = "All";
  final List<String> _filters = ["All", "Daily Activity", "Brain", "Memory", "Relaxation"];

  // 3. Game Data List (Makes filtering and building the UI much easier)
  final List<GameItem> _allGames = [
    GameItem(
      title: "Bubble Breathing",
      description: "Relax and focus on your breath as you blow up the bubble.",
      tag: "Relaxation",
      screen: BubbleBreathingGame(),
    ),
    GameItem(
      title: "Color Match",
      description: "Matches colors to their names.",
      tag: "Brain",
      screen: ColorMatch(),
    ),
    GameItem(
      title: "Emotion Garden",
      description: "Grow your own emotion garden.",
      tag: "Daily Activity",
      screen: EmotionGarden(),
    ),
    GameItem(
      title: "Cards Match",
      description: "Match the cards.",
      tag: "Memory",
      screen: MemoryCard(),
    ),
    GameItem(
      title: "Road Connect",
      description: "Connect the rounds.",
      tag: "Brain",
      screen: RoadConnect(),
    ),
    GameItem(
      title: "Catch Drops",
      description: "Catch the falling drops.",
      tag: "Brain",
      screen: CollectDropsGameScreen(),
    ),
  ];

  // Function to scroll to the All Games section
  void _scrollToAllGames() {
    if (_allGamesKey.currentContext != null) {
      Scrollable.ensureVisible(
        _allGamesKey.currentContext!,
        duration: Duration(milliseconds: 600),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    // Filter the list based on the selected tag
    List<GameItem> filteredGames = _selectedFilter == "All"
        ? _allGames
        : _allGames.where((game) => game.tag == _selectedFilter).toList();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        title: Text(
          "Mini Games",
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
            fontSize: 20.0,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Container(
          padding: EdgeInsets.all(15.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Let's play some games",
                style: TextStyle(color: AppColors.textDark),
              ),
              SizedBox(height: 20.0),
              
              // --- FEATURED SECTION ---
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12.0),
                  color: AppColors.lighterblue,
                ),
                padding: EdgeInsets.symmetric(horizontal: 20.0, vertical: 20.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    Text(
                      "Recommended for you",
                      style: TextStyle(color: AppColors.textDark, fontSize: 15.0),
                    ),
                    SizedBox(height: 10.0),
                    Text(
                      "Game Name",
                      style: TextStyle(
                        color: AppColors.textDark,
                        fontSize: 20.0,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 10.0),
                    Text(
                      "Description",
                      style: TextStyle(color: AppColors.textDark, fontSize: 15.0),
                    ),
                    SizedBox(height: 15.0),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        TextButton(
                          // SCROLL ACTION TRIGGERED HERE
                          onPressed: _scrollToAllGames, 
                          style: TextButton.styleFrom(
                            backgroundColor: AppColors.textDark,
                            foregroundColor: AppColors.background,
                            padding: EdgeInsets.symmetric(horizontal: 30.0, vertical: 15.0)
                          ),
                          child: Text(
                            "Play Solo",
                            style: TextStyle(fontWeight: FontWeight.bold),
                          )
                        ),
                        OutlinedButton(
                          onPressed: () {
                            // This directs the user to your new Community Games UI
                            Navigator.push(
                              context,
                              MaterialPageRoute(builder: (context) => const CommunityGamesScreen()),
                            );
                          },
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 30.0, vertical: 15.0),
                            side: const BorderSide(color: AppColors.textDark, width: 2.0),
                            foregroundColor: AppColors.textDark,
                          ),
                          child: const Text(
                            "With Community",
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    )
                  ],
                ),
              ),
              
              SizedBox(height: 25.0),
              
              // --- ALL GAMES TITLE (Target for scrolling) ---
              Text(
                "All Games",
                key: _allGamesKey, // Attached Key here
                style: TextStyle(
                  color: AppColors.textDark,
                  fontWeight: FontWeight.bold,
                  fontSize: 15.0
                ),
              ),
              SizedBox(height: 15.0),

              // --- FILTERS SECTION ---
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: _filters.map((filter) {
                    bool isSelected = _selectedFilter == filter;
                    return Padding(
                      padding: const EdgeInsets.only(right: 10.0),
                      child: ChoiceChip(
                        label: Text(filter),
                        selected: isSelected,
                        selectedColor: AppColors.lighterblue,
                        backgroundColor: AppColors.background,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.white : AppColors.textDark,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                        onSelected: (bool selected) {
                          setState(() {
                            _selectedFilter = filter;
                          });
                        },
                      ),
                    );
                  }).toList(),
                ),
              ),
              SizedBox(height: 15.0),
              
              // --- DYNAMIC GAMES LIST ---
              ...filteredGames.map((game) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10.0),
                  child: InkWell(
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => game.screen),
                      );
                    },
                    child: Container(
                      padding: EdgeInsets.all(20.0),
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: AppColors.blue,
                          width: 2.0,
                          style: BorderStyle.solid,
                        ),
                        borderRadius: BorderRadius.circular(15.0),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.spaceAround,
                              children: [
                                Text(
                                  game.title,   
                                  style: TextStyle(
                                    color: AppColors.lighterblue,
                                    fontSize: 18.0,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 10.0),
                                Text(
                                  game.description, 
                                  style: TextStyle(color: AppColors.textDark),
                                  softWrap: true,
                                )
                              ],
                            ),
                          ),
                          SizedBox(width: 10),
                          Container(
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(20.0),
                              color: AppColors.blue,
                            ),
                            padding: EdgeInsets.all(8.0),
                            child: Text(
                              game.tag, 
                              style: TextStyle(color: AppColors.textDark),
                            ),
                          )
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
              // Fallback if filter returns empty (just in case)
              if (filteredGames.isEmpty)
                Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Text("No games found for this category.", style: TextStyle(color: AppColors.textDark)),
                  ),
                )
            ],
          ),
        ),
      ),
    );
  }
}
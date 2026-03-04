import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart'; 

class MemoryCard extends StatefulWidget {
  @override
  _MemoryCardState createState() => _MemoryCardState();
}

class _MemoryCardState extends State<MemoryCard> {
  // Game Configuration
  int level = 1;
  int moves = 0;
  
  // State
  List<String> gridCards = [];
  List<bool> cardFlipped = []; // Tracks manual flips
  List<bool> cardMatched = []; // Tracks matches
  List<int> selectedIndices = [];
  
  bool isProcessing = false; // Block input during match check
  bool isPeeking = false;    // Block input during initial peek
  Timer? _peekTimer;         // Timer for the peek phase

  // Card Content (Emojis)
  final List<String> allEmojis = [
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", 
    "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔",
    "🦄", "🐝", "🐞", "🦋"
  ];

  @override
  void initState() {
    super.initState();
    startLevel(1);
  }

  @override
  void dispose() {
    _peekTimer?.cancel();
    super.dispose();
  }

  void startLevel(int newLevel) {
    _peekTimer?.cancel(); // Cancel any existing timer

    setState(() {
      level = newLevel;
      moves = 0;
      selectedIndices = [];
      isProcessing = false;
      isPeeking = true; // Enable peek mode immediately

      // Determine Grid Size
      int pairCount;
      if (level == 1) pairCount = 6;      // 12 cards
      else if (level == 2) pairCount = 8; // 16 cards
      else pairCount = 10;                // 20 cards

      // Generate Pairs
      List<String> gameEmojis = allEmojis.sublist(0, pairCount);
      gridCards = [...gameEmojis, ...gameEmojis]; 
      gridCards.shuffle(); 

      // Reset State
      cardFlipped = List.generate(gridCards.length, (index) => false);
      cardMatched = List.generate(gridCards.length, (index) => false);
    });

    // Hide cards after 3 seconds
    _peekTimer = Timer(Duration(seconds: 3), () {
      if (mounted) {
        setState(() {
          isPeeking = false;
        });
      }
    });
  }

  void onCardTap(int index) {
    // Block interaction if: Peeking, Processing, Already Flipped, or Already Matched
    if (isPeeking || isProcessing || cardFlipped[index] || cardMatched[index]) return;

    setState(() {
      cardFlipped[index] = true;
      selectedIndices.add(index);
    });

    if (selectedIndices.length == 2) {
      checkForMatch();
    }
  }

  void checkForMatch() {
    isProcessing = true;
    moves++;

    int index1 = selectedIndices[0];
    int index2 = selectedIndices[1];

    if (gridCards[index1] == gridCards[index2]) {
      // MATCH FOUND
      Timer(Duration(milliseconds: 500), () {
        if (mounted) {
          setState(() {
            cardMatched[index1] = true;
            cardMatched[index2] = true;
            selectedIndices.clear();
            isProcessing = false;
          });
          checkWinCondition();
        }
      });
    } else {
      // NO MATCH - Flip back
      Timer(Duration(milliseconds: 1000), () {
        if (mounted) {
          setState(() {
            cardFlipped[index1] = false;
            cardFlipped[index2] = false;
            selectedIndices.clear();
            isProcessing = false;
          });
        }
      });
    }
  }

  void checkWinCondition() {
    if (cardMatched.every((bool matched) => matched)) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          backgroundColor: AppColors.background,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text("Level $level Complete! 🎉", textAlign: TextAlign.center),
          content: Text(
            "You finished in $moves moves.",
            textAlign: TextAlign.center,
          ),
          actionsAlignment: MainAxisAlignment.center,
          actions: [
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.textDark,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () {
                Navigator.pop(context);
                if (level < 3) {
                  startLevel(level + 1);
                } else {
                  startLevel(1); // Reset to level 1
                }
              },
              child: Text(
                level < 3 ? "Next Level" : "Play Again",
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    int crossAxisCount = 4;
    
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        centerTitle: true,
        iconTheme: IconThemeData(color: AppColors.textDark),
        title: Text(
          "Memory Match",
          style: TextStyle(color: AppColors.titletext, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: () => startLevel(level),
          )
        ],
      ),
      body: Column(
        children: [
          // Header Stats
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Level $level",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark),
                ),
                // Status Text (Memorize vs Play)
                AnimatedSwitcher(
                  duration: Duration(milliseconds: 300),
                  child: Text(
                    isPeeking ? "Memorize! 👀" : "Find Pairs! 🎮",
                    key: ValueKey(isPeeking),
                    style: TextStyle(
                      fontSize: 18, 
                      fontWeight: FontWeight.bold, 
                      color: isPeeking ? Colors.orange : AppColors.blue
                    ),
                  ),
                ),
                Text(
                  "Moves: $moves",
                  style: TextStyle(fontSize: 18, color: AppColors.textDark.withOpacity(0.7)),
                ),
              ],
            ),
          ),
          
          // Centered Grid Area
          Expanded(
            child: Center( // Centers the grid vertically
              child: SingleChildScrollView( // Prevents overflow on small screens
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: GridView.builder(
                    shrinkWrap: true, // Only take up needed space
                    physics: NeverScrollableScrollPhysics(), // Disable internal scroll
                    itemCount: gridCards.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: crossAxisCount,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                      childAspectRatio: 0.8, // Slightly taller cards
                    ),
                    itemBuilder: (context, index) {
                      // Logic: Show card content if matched, manually flipped, OR peeking
                      bool showContent = cardMatched[index] || cardFlipped[index] || isPeeking;

                      return GestureDetector(
                        onTap: () => onCardTap(index),
                        child: AnimatedContainer(
                          duration: Duration(milliseconds: 400),
                          curve: Curves.easeInOut,
                          decoration: BoxDecoration(
                            color: showContent
                              ? (cardMatched[index] ? Colors.green.withOpacity(0.2) : Colors.white)
                              : AppColors.lighterblue, // Back of card color
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: cardMatched[index] 
                                  ? Colors.green 
                                  : (isPeeking ? Colors.orange : AppColors.blue),
                              width: 2,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.1),
                                blurRadius: 4,
                                offset: Offset(0, 4),
                              )
                            ],
                          ),
                          child: Center(
                            child: showContent
                                ? Text(
                                    gridCards[index],
                                    style: TextStyle(fontSize: 32),
                                  )
                                : Icon(
                                    Icons.help_outline,
                                    color: Colors.white,
                                    size: 30,
                                  ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
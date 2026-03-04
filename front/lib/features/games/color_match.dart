import 'dart:math';
import 'package:flutter/material.dart';
import '../../theme/app_colors.dart'; 

// // --- MAIN FOR TESTING ---
// void main() {
//   runApp(const MaterialApp(
//     debugShowCheckedModeBanner: false,
//     home: ASDColorGame(),
//   ));
// }
// ------------------------

class ColorMatch extends StatefulWidget {
  const ColorMatch({super.key});

  @override
  State<ColorMatch> createState() => _ColorMatchState();
}

class _ColorMatchState extends State<ColorMatch> {
  // 1. MASTER LIST (20 Options)
  final List<Map<String, dynamic>> masterGameItems = [
    {'color': Colors.red, 'name': 'Red', 'icon': Icons.favorite},
    {'color': Colors.blue, 'name': 'Blue', 'icon': Icons.water_drop},
    {'color': Colors.green, 'name': 'Green', 'icon': Icons.grass},
    {'color': Colors.orange, 'name': 'Orange', 'icon': Icons.wb_sunny},
    {'color': Colors.purple, 'name': 'Purple', 'icon': Icons.bedroom_baby},
    {'color': Colors.pink, 'name': 'Pink', 'icon': Icons.local_florist},
    {'color': Colors.brown, 'name': 'Brown', 'icon': Icons.pets},
    {'color': Colors.teal, 'name': 'Teal', 'icon': Icons.diamond},
    {'color': Colors.yellow, 'name': 'Yellow', 'icon': Icons.star},
    {'color': Colors.cyan, 'name': 'Cyan', 'icon': Icons.flight},           
    {'color': Colors.lime, 'name': 'Lime', 'icon': Icons.face},             
    {'color': Colors.indigo, 'name': 'Indigo', 'icon': Icons.directions_bus}, 
    {'color': Colors.grey, 'name': 'Grey', 'icon': Icons.cloud},            
    {'color': Colors.amber, 'name': 'Amber', 'icon': Icons.lightbulb},      
    {'color': Colors.deepPurple, 'name': 'Deep Purple', 'icon': Icons.music_note}, 
    {'color': Colors.lightGreen, 'name': 'Light Green', 'icon': Icons.eco}, 
    {'color': Colors.deepOrange, 'name': 'Deep Orange', 'icon': Icons.local_fire_department}, 
    {'color': Colors.blueGrey, 'name': 'Blue Grey', 'icon': Icons.anchor},  
    {'color': Colors.black, 'name': 'Black', 'icon': Icons.nightlight_round}, 
    {'color': const Color(0xFF8B4513), 'name': 'Choco', 'icon': Icons.cake}, 
  ];

  // Game State
  List<Map<String, dynamic>> currentRoundItems = [];
  late Map<String, dynamic> targetItem;
  List<Color> hiddenItems = []; 
  bool showSuccess = false;

  // --- DIFFICULTY SETTINGS ---
  // Default is Normal (6)
  int gridSize = 6; 

  @override
  void initState() {
    super.initState();
    startNewRound();
  }

  void startNewRound() {
    setState(() {
      hiddenItems.clear();
      showSuccess = false;

      var shuffledList = List<Map<String, dynamic>>.from(masterGameItems)..shuffle();
      currentRoundItems = shuffledList.take(gridSize).toList();
      targetItem = currentRoundItems[Random().nextInt(currentRoundItems.length)];
    });
  }

  void checkSelection(Map<String, dynamic> selectedItem) {
    setState(() {
      if (selectedItem['color'] == targetItem['color']) {
        showSuccess = true;
        Future.delayed(const Duration(milliseconds: 1500), () {
          if (mounted) startNewRound();
        });
      } else {
        hiddenItems.add(selectedItem['color'] as Color);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (currentRoundItems.isEmpty) return const SizedBox();

    Color targetColor = targetItem['color'] as Color;
    IconData targetIcon = targetItem['icon'] as IconData;
    String targetName = targetItem['name'] as String;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          "Color Match",
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w600,
            fontSize: 20,
          ),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        centerTitle: false, 
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, color: AppColors.lighterblue),
          onPressed: () {
            if (Navigator.canPop(context)) {
              Navigator.pop(context);
            }
          },
        ),
        actions: [
          // --- DROPDOWN MENU ---
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            margin: const EdgeInsets.only(right: 16, top: 8, bottom: 8),
            decoration: BoxDecoration(
              color: AppColors.lighterblue.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.lighterblue, width: 1.5),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<int>(
                value: gridSize,
                icon: const Icon(Icons.arrow_drop_down, color: AppColors.lighterblue),
                style: const TextStyle(
                  color: AppColors.lighterblue,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
                dropdownColor: AppColors.background,
                borderRadius: BorderRadius.circular(12),
                items: const [
                  DropdownMenuItem(
                    value: 4,
                    child: Text("Easy"),
                  ),
                  DropdownMenuItem(
                    value: 6,
                    child: Text("Normal"),
                  ),
                  DropdownMenuItem(
                    value: 9,
                    child: Text("Hard"),
                  ),
                ],
                onChanged: (int? newValue) {
                  if (newValue != null) {
                    setState(() {
                      gridSize = newValue;
                      startNewRound(); // Restart game immediately on change
                    });
                  }
                },
              ),
            ),
          ),
        ],
      ),
      
      body: Center(
        child: SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // --- INSTRUCTION AREA ---
              Text(
                showSuccess ? "Good Job!" : "Find $targetName",
                style: const TextStyle(
                  fontSize: 32, 
                  fontWeight: FontWeight.bold,
                  color: AppColors.textDark, 
                ),
              ),
              const SizedBox(height: 24),
              
              // --- TARGET DISPLAY ---
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: 130,
                height: 130,
                decoration: BoxDecoration(
                  color: showSuccess ? targetColor : AppColors.blue.withOpacity(0.1), 
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: showSuccess ? targetColor : AppColors.lighterblue.withOpacity(0.5), 
                    width: 4
                  ),
                ),
                child: Center(
                  child: showSuccess 
                      ? const Icon(Icons.check, size: 70, color: AppColors.background)
                      : Icon(targetIcon, size: 70, color: targetColor),
                ),
              ),
              
              const SizedBox(height: 40),

              // --- BUTTONS GRID ---
              Wrap(
                spacing: 15,
                runSpacing: 15,
                alignment: WrapAlignment.center,
                children: currentRoundItems.map<Widget>((item) {
                  Color itemColor = item['color'] as Color;
                  IconData itemIcon = item['icon'] as IconData;
                  bool isHidden = hiddenItems.contains(itemColor);

                  return IgnorePointer(
                    ignoring: isHidden || showSuccess,
                    child: AnimatedOpacity(
                      duration: const Duration(milliseconds: 500),
                      opacity: isHidden ? 0.0 : 1.0,
                      child: GestureDetector(
                        onTap: () => checkSelection(item),
                        child: Container(
                          // Dynamic Sizing logic
                          width: gridSize > 6 ? 80 : 100, 
                          height: gridSize > 6 ? 80 : 100,
                          decoration: BoxDecoration(
                            color: itemColor,
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: itemColor.withOpacity(0.4),
                                blurRadius: 8,
                                offset: const Offset(0, 4),
                              )
                            ],
                          ),
                          child: Icon(
                            itemIcon, 
                            color: Colors.white.withOpacity(0.9), 
                            size: gridSize > 6 ? 35 : 50, 
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
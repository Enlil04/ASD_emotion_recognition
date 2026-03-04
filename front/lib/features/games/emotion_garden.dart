import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';
import '../../services/api_service.dart';

class EmotionGarden extends StatefulWidget {
  @override
  _EmotionGardenState createState() => _EmotionGardenState();
}

class _EmotionGardenState extends State<EmotionGarden> {
  final PageController _pageController = PageController(viewportFraction: 0.85);
  int _currentPage = 0;

  final int maxStage = 4;

  // Data for the 3 Pots
  List<Map<String, dynamic>> pots = [
    {"id": 0, "type": null, "stage": 0, "lastWatered": ""},
    {"id": 1, "type": null, "stage": 0, "lastWatered": ""},
    {"id": 2, "type": null, "stage": 0, "lastWatered": ""}
  ];

  // Harvested History
  List<String> bouquet = []; // Stores "Type|Date" strings

  // Seed Options
  final List<Map<String, String>> seeds = [
    {"name": "Happiness", "emoji": "🌻", "desc": "Grow your joy"},
    {"name": "Calm", "emoji": "🪷", "desc": "Find your peace"},
    {"name": "Love", "emoji": "🌹", "desc": "Nurture gratitude"},
  ];

  @override
  void initState() {
    super.initState();
    _loadGardenData();
  }

  // --- DATA MANAGEMENT ---

  String _getTodayKey() {
    DateTime now = DateTime.now();
    return "${now.year}-${now.month}-${now.day}";
  }

  Future<void> _loadGardenData() async {
    try {
      final cloudData = await ApiService.fetchGardenData();
      
      setState(() {
        // 1. Map the backend pots to your local 'pots' list
        for (var pot in cloudData['pots']) {
          int idx = pot['pot_index'];
          pots[idx] = {
            "id": idx,
            "type": pot['seed_type'],
            "stage": pot['stage'] ?? 0,
            "lastWatered": pot['last_watered'] ?? "",
          };
        }
        
        // 2. Map the backend bouquet history
        bouquet = (cloudData['bouquet'] as List).map((b) {
          return "${b['plant_type']}|${b['harvest_date']}";
        }).toList();
      });
    } catch (e) {
      print("Error syncing garden: $e");
    }
  }

  Future<void> _plantSeed(int potIndex, String seedType) async {
    // 1. Update UI immediately
    setState(() {
      pots[potIndex]["type"] = seedType;
      pots[potIndex]["stage"] = 0;
      pots[potIndex]["lastWatered"] = ""; 
    });

    // 2. Sync to backend
    try {
      await ApiService.plantSeed(potIndex, seedType);
    } catch (e) {
      print("Failed to plant seed on server: $e");
    }
  }

  Future<void> _waterPlant(int potIndex) async {
    String today = _getTodayKey();
    if (pots[potIndex]["lastWatered"] == today) return;

    // 1. Update UI immediately
    setState(() {
      pots[potIndex]["stage"] += 1;
      pots[potIndex]["lastWatered"] = today;
    });

    // 2. Sync to backend
    try {
      await ApiService.waterPlant(potIndex, today);
    } catch (e) {
      print("Failed to sync water action to server: $e");
    }
  }

  Future<void> _harvestPlant(int potIndex) async {
    String type = pots[potIndex]["type"];
    String date = _getTodayKey();

    // 1. Update UI immediately
    setState(() {
      bouquet.add("$type|$date"); 
      pots[potIndex]["type"] = null;
      pots[potIndex]["stage"] = 0;
      pots[potIndex]["lastWatered"] = "";
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("Harvested $type! Added to your bouquet."),
        backgroundColor: Colors.green,
      ),
    );

    // 2. Sync to backend
    try {
      await ApiService.harvestPlant(potIndex, type, date);
    } catch (e) {
      print("Failed to sync harvest to server: $e");
    }
  }

  // --- HELPERS ---

  String _getPlantEmoji(String type, int stage) {
    if (stage == 0) return "🌱"; 
    if (stage == 1) return "🌿"; 
    if (stage == 2) return "🌳"; 
    if (stage == 3) return "🌺"; 
    
    if (type == "Happiness") return "🌻";
    if (type == "Calm") return "🪷";
    if (type == "Love") return "🌹";
    return "🌼";
  }

  Color _getPotColor(String? type) {
    if (type == "Happiness") return Colors.yellow.shade100;
    if (type == "Calm") return Colors.blue.shade100;
    if (type == "Love") return Colors.red.shade100;
    return AppColors.lighterblue; 
  }

  // --- BOUQUET SCREEN (MODAL) ---
  void _showBouquet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.8,
          decoration: BoxDecoration(
            color: AppColors.background,
            borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
          ),
          child: Column(
            children: [
              SizedBox(height: 20),
              Container(
                width: 50, height: 5,
                decoration: BoxDecoration(color: Colors.grey[300], borderRadius: BorderRadius.circular(10)),
              ),
              SizedBox(height: 20),
              Text(
                "My Harvested Bouquet",
                style: TextStyle(
                  fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.titletext
                ),
              ),
              SizedBox(height: 20),
              Expanded(
                child: bouquet.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.local_florist_outlined, size: 60, color: Colors.grey[300]),
                        SizedBox(height: 10),
                        Text("No flowers yet. Keep growing!", style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  )
                : GridView.builder(
                    padding: EdgeInsets.all(20),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 15,
                      mainAxisSpacing: 15,
                      childAspectRatio: 0.8,
                    ),
                    itemCount: bouquet.length,
                    itemBuilder: (context, index) {
                      final parts = bouquet[bouquet.length - 1 - index].split('|'); 
                      final type = parts[0];
                      final date = parts.length > 1 ? parts[1] : "";
                      
                      return Container(
                        decoration: BoxDecoration(
                          color: _getPotColor(type).withOpacity(0.5),
                          borderRadius: BorderRadius.circular(15),
                          border: Border.all(color: AppColors.lighterblue),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(_getPlantEmoji(type, 4), style: TextStyle(fontSize: 30)),
                            SizedBox(height: 5),
                            Text(
                              type, 
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textDark)
                            ),
                            Text(
                              date, 
                              style: TextStyle(fontSize: 10, color: AppColors.textDark.withOpacity(0.6))
                            ),
                          ],
                        ),
                      );
                    },
                  ),
              ),
            ],
          ),
        );
      },
    );
  }

  // --- UI BUILDERS ---

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        title: Text(
          "My Garden",
          style: TextStyle(
            color: AppColors.titletext,
            fontSize: 22,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: Icon(Icons.local_florist, color: AppColors.textDark),
            onPressed: _showBouquet,
            tooltip: "View Bouquet",
          )
        ],
      ),
      body: Column(
        children: [
          SizedBox(height: 20),
          Text(
            "Swipe to view your pots",
            style: TextStyle(color: AppColors.textDark.withOpacity(0.5)),
          ),
          SizedBox(height: 20),
          
          Expanded(
            child: PageView.builder(
              controller: _pageController,
              itemCount: 3,
              onPageChanged: (int index) {
                setState(() => _currentPage = index);
              },
              itemBuilder: (context, index) {
                return _buildPotCard(index);
              },
            ),
          ),
          
          SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(3, (index) {
              return Container(
                margin: EdgeInsets.symmetric(horizontal: 4),
                width: _currentPage == index ? 12 : 8,
                height: _currentPage == index ? 12 : 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _currentPage == index 
                      ? AppColors.textDark 
                      : AppColors.textDark.withOpacity(0.3),
                ),
              );
            }),
          ),
          SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildPotCard(int index) {
    bool isEmpty = pots[index]["type"] == null;
    String? type = pots[index]["type"];
    int stage = pots[index]["stage"];
    String lastWatered = pots[index]["lastWatered"];
    bool isWateredToday = lastWatered == _getTodayKey();

    return AnimatedContainer(
      duration: Duration(milliseconds: 300),
      margin: EdgeInsets.symmetric(horizontal: 10, vertical: 20),
      decoration: BoxDecoration(
        color: isEmpty ? Colors.white : _getPotColor(type),
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 5),
          )
        ],
        border: Border.all(
          color: AppColors.lighterblue,
          width: 2,
        ),
      ),
      child: isEmpty 
          ? _buildEmptyState(index) 
          : _buildPlantedState(index, type!, stage, isWateredToday),
    );
  }

  Widget _buildEmptyState(int index) {
    return Padding(
      padding: EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.eco_outlined, size: 60, color: AppColors.textDark.withOpacity(0.5)),
          SizedBox(height: 20),
          Text(
            "This pot is empty",
            style: TextStyle(
              fontSize: 20, 
              fontWeight: FontWeight.bold,
              color: AppColors.textDark
            ),
          ),
          Text(
            "Choose a seed to plant:",
            style: TextStyle(color: AppColors.textDark.withOpacity(0.7)),
          ),
          SizedBox(height: 30),
          ...seeds.map((seed) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 12.0),
              child: InkWell(
                onTap: () => _plantSeed(index, seed["name"]!),
                child: Container(
                  padding: EdgeInsets.symmetric(vertical: 15, horizontal: 20),
                  decoration: BoxDecoration(
                    color: AppColors.lighterblue.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(15),
                    border: Border.all(color: AppColors.lighterblue),
                  ),
                  child: Row(
                    children: [
                      Text(seed["emoji"]!, style: TextStyle(fontSize: 24)),
                      SizedBox(width: 15),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            seed["name"]!,
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: AppColors.textDark,
                            ),
                          ),
                          Text(
                            seed["desc"]!,
                            style: TextStyle(
                              fontSize: 12,
                              color: AppColors.textDark.withOpacity(0.6),
                            ),
                          ),
                        ],
                      ),
                      Spacer(),
                      Icon(Icons.add_circle_outline, color: AppColors.textDark),
                    ],
                  ),
                ),
              ),
            );
          }).toList()
        ],
      ),
    );
  }

  Widget _buildPlantedState(int index, String type, int stage, bool isWateredToday) {
    bool isFullyGrown = stage >= maxStage;

    return Stack(
      children: [
        Align(
          alignment: Alignment.bottomCenter,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 40.0),
            child: Opacity(
              opacity: 0.2,
              child: Icon(Icons.local_florist, size: 200, color: Colors.brown),
            ),
          ),
        ),
        
        Padding(
          padding: EdgeInsets.all(25),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.6),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      "Pot ${index + 1}",
                      style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.textDark),
                    ),
                  ),
                  if (isFullyGrown)
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.green,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        "Ready!",
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                      ),
                    ),
                ],
              ),

              Column(
                children: [
                  AnimatedSwitcher(
                    duration: Duration(milliseconds: 500),
                    transitionBuilder: (Widget child, Animation<double> animation) {
                      return ScaleTransition(scale: animation, child: child);
                    },
                    child: Text(
                      _getPlantEmoji(type, stage),
                      key: ValueKey<int>(stage), 
                      style: TextStyle(fontSize: 100),
                    ),
                  ),
                  SizedBox(height: 20),
                  Text(
                    type,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textDark,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    isFullyGrown 
                        ? "Your plant is fully grown!" 
                        : "Level $stage / $maxStage",
                    style: TextStyle(color: AppColors.textDark.withOpacity(0.7)),
                  ),
                ],
              ),

              SizedBox(
                width: double.infinity,
                child: isFullyGrown 
                ? ElevatedButton.icon(
                    onPressed: () => _harvestPlant(index),
                    icon: Icon(Icons.cut),
                    label: Text("Harvest & Clear Pot"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.orange,
                      foregroundColor: Colors.white,
                      padding: EdgeInsets.symmetric(vertical: 15),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                    ),
                  )
                : ElevatedButton.icon(
                    onPressed: isWateredToday ? null : () => _waterPlant(index),
                    icon: Icon(isWateredToday ? Icons.check : Icons.water_drop),
                    label: Text(
                      isWateredToday ? "Come back tomorrow" : "Water Plant",
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.textDark,
                      foregroundColor: AppColors.background,
                      disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                      disabledForegroundColor: Colors.grey.shade600,
                      padding: EdgeInsets.symmetric(vertical: 15),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                    ),
                  ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
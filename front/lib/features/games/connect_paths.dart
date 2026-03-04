import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart'; // Ensure match



// --- DATA CLASSES ---

class Point {
  final int row, col;
  Point(this.row, this.col);
  @override
  bool operator ==(Object other) => other is Point && row == other.row && col == other.col;
  @override
  int get hashCode => row.hashCode ^ col.hashCode;
}

class Dot {
  final Point point;
  final int colorIndex;
  Dot(this.point, this.colorIndex);
}

class LevelData {
  final int rows, cols, colors;
  final List<Dot> dots;
  LevelData({required this.rows, required this.cols, required this.dots, required this.colors});
}

// --- RANDOM LEVEL GENERATOR (GUARANTEES SOLVABILITY) ---

class LevelGenerator {
  static LevelData generate(int gridSize, int numColors) {
    Random rand = Random();
    
    // Keep trying until we successfully place all colors without getting trapped
    while (true) {
      List<List<int>> grid = List.generate(gridSize, (_) => List.filled(gridSize, -1));
      List<Dot> dots = [];
      bool success = true;

      for (int c = 0; c < numColors; c++) {
        // 1. Find all empty cells to start a new color path
        List<Point> emptyCells = [];
        for (int r = 0; r < gridSize; r++) {
          for (int col = 0; col < gridSize; col++) {
            if (grid[r][col] == -1) emptyCells.add(Point(r, col));
          }
        }
        
        if (emptyCells.isEmpty) { 
          success = false; 
          break; 
        }

        // 2. Pick a random start point
        emptyCells.shuffle(rand);
        Point start = emptyCells.first;
        grid[start.row][start.col] = c;
        Point current = start;
        
        int pathLength = 1;
        // Try to make paths longer to fill up the board more
        int targetLength = 3 + rand.nextInt(gridSize); 

        // 3. Random walk to create the path
        for (int step = 0; step < targetLength; step++) {
          List<Point> neighbors = [
            Point(current.row - 1, current.col),
            Point(current.row + 1, current.col),
            Point(current.row, current.col - 1),
            Point(current.row, current.col + 1),
          ];
          
          // Only allow moving to empty spaces
          neighbors.retainWhere((p) =>
            p.row >= 0 && p.row < gridSize &&
            p.col >= 0 && p.col < gridSize &&
            grid[p.row][p.col] == -1
          );

          if (neighbors.isEmpty) break; // Trapped, stop path here

          neighbors.shuffle(rand);
          current = neighbors.first;
          grid[current.row][current.col] = c;
          pathLength++;
        }

        // 4. A path must be at least 2 blocks long to be playable
        if (pathLength < 2) { 
          success = false; 
          break; 
        }
        
        // 5. Save the start and end points as the Dots for this color
        dots.add(Dot(start, c));
        dots.add(Dot(current, c));
      }

      // If we placed all colors successfully, return the level!
      if (success) {
        return LevelData(rows: gridSize, cols: gridSize, colors: numColors, dots: dots);
      }
    }
  }
}

// --- LEVEL SELECTION SCREEN ---


// --- PAINTER ---

class FlowPainter extends CustomPainter {
  final LevelData level;
  final Map<int, List<Point>> paths;

  FlowPainter({required this.level, required this.paths});

  // The colors for the dots and pipes
  final List<Color> gameColors = [
    Color(0xFFEF5350), // Red
    Color(0xFF42A5F5), // Blue
    Color(0xFF66BB6A), // Green
    Color(0xFFFFA726), // Orange
    Color(0xFFAB47BC), // Purple
    Color(0xFF26C6DA), // Cyan
    Color(0xFFEC407A), // Pink
  ];

  @override
  void paint(Canvas canvas, Size size) {
    double cellW = size.width / level.cols;
    double cellH = size.height / level.rows;

    Paint gridLine = Paint()
      ..color = Colors.grey.withOpacity(0.2)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    // 1. Draw Grid Lines
    for (int i = 1; i < level.cols; i++) {
      canvas.drawLine(Offset(i * cellW, 0), Offset(i * cellW, size.height), gridLine);
    }
    for (int i = 1; i < level.rows; i++) {
      canvas.drawLine(Offset(0, i * cellH), Offset(size.width, i * cellH), gridLine);
    }

    // 2. Draw Paths (Pipes)
    paths.forEach((colorIdx, points) {
      if (points.isEmpty) return;
      Color c = gameColors[colorIdx % gameColors.length];
      
      Paint pathPaint = Paint()
        ..color = c.withOpacity(0.4) // Semi-transparent pipe
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = cellW * 0.45; // Thick pipe

      Path path = Path();
      path.moveTo(_cX(points[0], cellW), _cY(points[0], cellH));
      
      for (int i = 1; i < points.length; i++) {
        path.lineTo(_cX(points[i], cellW), _cY(points[i], cellH));
      }
      canvas.drawPath(path, pathPaint);
    });

    // 3. Draw Dots
    for (var dot in level.dots) {
      Color c = gameColors[dot.colorIndex % gameColors.length];
      
      // Outer colored circle
      canvas.drawCircle(Offset(_cX(dot.point, cellW), _cY(dot.point, cellH)), cellW * 0.35, Paint()..color = c);
      // Inner white shine
      canvas.drawCircle(Offset(_cX(dot.point, cellW), _cY(dot.point, cellH)), cellW * 0.15, Paint()..color = Colors.white.withOpacity(0.4));
    }
  }
  
  // Helpers to get Center X/Y of a cell
  double _cX(Point p, double w) => (p.col * w) + w / 2;
  double _cY(Point p, double h) => (p.row * h) + h / 2;

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
// --- GAME SCREEN ---
// --- GAME SCREEN ---

class RoadConnect extends StatefulWidget {
  @override
  _RoadConnectState createState() => _RoadConnectState();
}

class _RoadConnectState extends State<RoadConnect> {
  // --- Difficulty State ---
  String currentDifficulty = "Easy";
  int currentGridSize = 5;
  int currentNumColors = 4;

  // --- Game State ---
  late LevelData currentLevel;
  Map<int, List<Point>> paths = {};
  int? draggingColor;

  double _gridSize = 0;
  double _cellSize = 0;

  @override
  void initState() {
    super.initState();
    _generateNewLevel();
  }

  void _generateNewLevel() {
    setState(() {
      // Use the state variables instead of widget parameters
      currentLevel = LevelGenerator.generate(currentGridSize, currentNumColors);
      paths = {};
      draggingColor = null;
    });
  }

  // --- Dropdown Handler ---
  void _changeDifficulty(String? newDifficulty) {
    if (newDifficulty == null || newDifficulty == currentDifficulty) return;
    
    setState(() {
      currentDifficulty = newDifficulty;
      if (newDifficulty == "Easy") {
        currentGridSize = 5;
        currentNumColors = 4;
      } else if (newDifficulty == "Medium") {
        currentGridSize = 6;
        currentNumColors = 5;
      } else if (newDifficulty == "Hard") {
        currentGridSize = 7;
        currentNumColors = 6;
      }
      _generateNewLevel(); // Instantly build a new board for the new difficulty
    });
  }

  void _onPanStart(DragStartDetails details, BoxConstraints constraints) {
    _handleTouch(details.localPosition, constraints, isStart: true);
  }

  void _onPanUpdate(DragUpdateDetails details, BoxConstraints constraints) {
    _handleTouch(details.localPosition, constraints, isStart: false);
  }

  void _onPanEnd(DragEndDetails details) {
    setState(() {
      draggingColor = null;
    });
    _checkWinCondition();
  }

  void _handleTouch(Offset localPosition, BoxConstraints constraints, {required bool isStart}) {
    _gridSize = constraints.maxWidth;
    _cellSize = _gridSize / currentLevel.cols;

    int col = (localPosition.dx / _cellSize).floor();
    int row = (localPosition.dy / _cellSize).floor();

    if (col < 0 || col >= currentLevel.cols || row < 0 || row >= currentLevel.rows) return;

    Point touchedPoint = Point(row, col);

    if (isStart) {
      for (var dot in currentLevel.dots) {
        if (dot.point == touchedPoint) {
          setState(() {
            draggingColor = dot.colorIndex;
            paths[draggingColor!] = [touchedPoint];
          });
          return;
        }
      }
      paths.forEach((color, path) {
        if (path.isNotEmpty && path.last == touchedPoint) {
           setState(() => draggingColor = color);
        }
      });
    } 
    else if (draggingColor != null) {
      List<Point> currentPath = paths[draggingColor!]!;
      Point lastPoint = currentPath.last;

      if (touchedPoint != lastPoint) {
         if (_isAdjacent(lastPoint, touchedPoint)) {
           setState(() {
             if (currentPath.length > 1 && currentPath[currentPath.length - 2] == touchedPoint) {
               currentPath.removeLast();
             } 
             else {
               if (!_isCellBlocked(touchedPoint, draggingColor!)) {
                 currentPath.add(touchedPoint);
               }
             }
           });
         }
      }
    }
  }

  bool _isAdjacent(Point a, Point b) {
    return (a.row == b.row && (a.col - b.col).abs() == 1) ||
           (a.col == b.col && (a.row - b.row).abs() == 1);
  }

  bool _isCellBlocked(Point p, int myColor) {
    for (var entry in paths.entries) {
      if (entry.key == myColor) {
        if (entry.value.contains(p)) return true;
      } else {
        if (entry.value.contains(p)) return true;
      }
    }
    for (var dot in currentLevel.dots) {
      if (dot.point == p && dot.colorIndex != myColor) return true;
    }
    return false;
  }

  void _checkWinCondition() {
    bool allConnected = true;

    for (int i = 0; i < currentLevel.colors; i++) {
      if (!paths.containsKey(i)) { allConnected = false; break; }
      
      List<Point> path = paths[i]!;
      List<Dot> myDots = currentLevel.dots.where((d) => d.colorIndex == i).toList();
      
      bool startMatch = path.first == myDots[0].point || path.first == myDots[1].point;
      bool endMatch = path.last == myDots[0].point || path.last == myDots[1].point;
      
      if (!startMatch || !endMatch || path.length < 2) {
        allConnected = false;
        break;
      }
    }

    if (allConnected) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          backgroundColor: AppColors.background,
          title: Text("Solved! 🎉", style: TextStyle(color: AppColors.textDark)),
          content: Text("Great job completing this $currentDifficulty puzzle!"),
          actions: [
             ElevatedButton(
               style: ElevatedButton.styleFrom(backgroundColor: AppColors.textDark),
               child: Text("Next Random Level"),
               onPressed: () {
                 Navigator.pop(ctx);
                 _generateNewLevel();
               },
             )
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        title: Text("Connect Flow", style: TextStyle(color: AppColors.titletext, fontWeight: FontWeight.bold)),
        actions: [
          // --- DROPDOWN ADDED HERE ---
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: currentDifficulty,
                dropdownColor: AppColors.background,
                icon: Icon(Icons.arrow_drop_down, color: AppColors.textDark),
                style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.bold, fontSize: 16),
                items: ["Easy", "Medium", "Hard"].map((String value) {
                  return DropdownMenuItem<String>(
                    value: value,
                    child: Text(value),
                  );
                }).toList(),
                onChanged: _changeDifficulty,
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.refresh, color: AppColors.textDark),
            onPressed: _generateNewLevel,
            tooltip: "New Random Board",
          )
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("$currentDifficulty Level", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark)),
                Text("${currentLevel.rows}x${currentLevel.cols} Grid | $currentNumColors Colors", style: TextStyle(color: Colors.grey)),
              ],
            ),
            SizedBox(height: 30),
            Expanded(
              child: Center(
                child: AspectRatio(
                  aspectRatio: 1.0,
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      return GestureDetector(
                        onPanStart: (d) => _onPanStart(d, constraints),
                        onPanUpdate: (d) => _onPanUpdate(d, constraints),
                        onPanEnd: _onPanEnd,
                        child: Container(
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(15),
                            boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 10, offset: Offset(0, 5))],
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(15),
                            child: CustomPaint(
                              painter: FlowPainter(level: currentLevel, paths: paths),
                              size: Size(constraints.maxWidth, constraints.maxHeight),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
            SizedBox(height: 30),
            Text("Drag to connect matching colors", style: TextStyle(color: Colors.grey)),
            SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
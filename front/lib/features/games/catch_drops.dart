import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';

class CollectDropsGameScreen extends StatefulWidget {
  const CollectDropsGameScreen({super.key});

  @override
  State<CollectDropsGameScreen> createState() => _CollectDropsGameScreenState();
}

class _CollectDropsGameScreenState extends State<CollectDropsGameScreen> {
  // --- Board config ---
  final int rows = 6;
  final int cols = 6;
  final int initialDrops = 6;

  // Nimi position (grid coordinates)
  int nimiRow = 1;
  int nimiCol = 0;

  // Drops positions as "r,c" keys -> type
  final Map<String, DropType> drops = {};

  // Barrier positions
  final Set<String> barriers = {};

  // Comments
  String comment = "Collect the drops";
  DropType? commentDrop;

  // Movement throttle
  DateTime _lastMove = DateTime.fromMillisecondsSinceEpoch(0);
  final Duration moveCooldown = const Duration(milliseconds: 160);

  // Random
  final Random _rng = Random();

  // Optional: continuous move when holding joystick
  Timer? _holdTimer;

  // --- Reward feedback (pop + ripple) ---
  double nimiScale = 1.0;
  Timer? _scaleTimer;

  String? rippleKey; // "r,c" of last collected drop
  int rippleToken = 0;
  Timer? _rippleTimer;

  // --- Quest system ---
  DropType questType = DropType.calm;
  int questTarget = 3;
  int questProgress = 0;
  bool questCompleted = false;

  // Optional: non-competitive reward counter
  int stars = 0;

  @override
  void initState() {
    super.initState();
    _generateQuest();
    _spawnDrops();
  }

  @override
  void dispose() {
    _holdTimer?.cancel();
    _scaleTimer?.cancel();
    _rippleTimer?.cancel();
    super.dispose();
  }

  // -----------------------
  // Quest
  // -----------------------
  void _generateQuest() {
    // Weighted distribution: calm most common (fits your drop spawn)
    final r = _rng.nextDouble();
    questType = (r < 0.55)
        ? DropType.calm
        : (r < 0.80)
            ? DropType.focus
            : DropType.energy;

    // Small achievable targets
    questTarget = (questType == DropType.calm) ? 3 : 2;

    questProgress = 0;
    questCompleted = false;
  }

  // -----------------------
  // Drops: spawn + types
  // -----------------------
  void _spawnDrops() {
    drops.clear();

    // Ensure we don't spawn on Nimi start
    final occupied = <String>{"$nimiRow,$nimiCol"};

    while (drops.length < initialDrops) {
      final r = _rng.nextInt(rows);
      final c = _rng.nextInt(cols);
      final key = "$r,$c";
      if (occupied.contains(key)) continue;

      // Weighted types (calm is most common)
      final p = _rng.nextDouble();
      final type = (p < 0.55)
          ? DropType.calm
          : (p < 0.80)
              ? DropType.focus
              : DropType.energy;

      drops[key] = type;
      occupied.add(key);
    }

    // Spawn 3–5 random barriers (not on Nimi or drops)
    barriers.clear();
    final barrierCount = 3 + _rng.nextInt(3);
    int attempts = 0;
    while (barriers.length < barrierCount && attempts < 100) {
      attempts++;
      final r = _rng.nextInt(rows);
      final c = _rng.nextInt(cols);
      final key = "$r,$c";
      if (occupied.contains(key)) continue;
      barriers.add(key);
      occupied.add(key);
    }

    setState(() {});
  }

  void _setComment(String text, {DropType? drop}) {
    setState(() {
      comment = text;
      commentDrop = drop;
    });
  }

  // -----------------------
  // Reward effects (pop + ripple)
  // -----------------------
  void _pulseNimi() {
    _scaleTimer?.cancel();
    setState(() => nimiScale = 1.12); // subtle

    _scaleTimer = Timer(const Duration(milliseconds: 160), () {
      if (!mounted) return;
      setState(() => nimiScale = 1.0);
    });
  }

  void _spawnRippleAt(String key) {
    _rippleTimer?.cancel();
    setState(() {
      rippleKey = key;
      rippleToken++;
    });

    final current = rippleToken;
    _rippleTimer = Timer(const Duration(milliseconds: 380), () {
      if (!mounted) return;
      if (rippleToken == current) {
        setState(() => rippleKey = null);
      }
    });
  }

  // -----------------------
  // Movement + collection
  // -----------------------
  void _tryMove(Dir dir) {
    final now = DateTime.now();
    if (now.difference(_lastMove) < moveCooldown) return;
    _lastMove = now;

    int newR = nimiRow;
    int newC = nimiCol;

    switch (dir) {
      case Dir.up:
        newR--;
        break;
      case Dir.down:
        newR++;
        break;
      case Dir.left:
        newC--;
        break;
      case Dir.right:
        newC++;
        break;
    }

    // Bounds check
    if (newR < 0 || newR >= rows || newC < 0 || newC >= cols) return;

    // Barrier check
    if (barriers.contains("$newR,$newC")) return;

    setState(() {
      nimiRow = newR;
      nimiCol = newC;
    });

    final key = "$nimiRow,$nimiCol";
    final DropType? collectedType = drops.remove(key);
    final bool collected = collectedType != null;

    if (collected) {
      // Reward feedback
      _pulseNimi();
      _spawnRippleAt(key);

      // Quest progress (only if quest not completed yet)
      if (!questCompleted && collectedType == questType) {
        questProgress++;
        if (questProgress >= questTarget) {
          questCompleted = true;
          stars++;
          _setComment("Quest complete, Great job!");
        }
      }

      // If quest is completed, keep that message; otherwise show type message
      if (!questCompleted) {
        switch (collectedType!) {
          case DropType.calm:
            _setComment("Calm drop collected", drop: DropType.calm);
            break;
          case DropType.focus:
            _setComment("Focus drop collected", drop: DropType.focus);
            break;
          case DropType.energy:
            _setComment("Energy drop collected", drop: DropType.energy);
            break;
        }
      }

      if (drops.isEmpty) {
        if (questCompleted) {
          _setComment("Level complete. Quest complete!");
        } else {
          _setComment("Level complete.");
        }
        _showWinDialog();
      }
    } else {
      // Occasionally speak while moving (keep calm)
      if (_rng.nextDouble() < 0.18) {
        const moveLines = [
          "Take it slow.",
          "You're doing fine.",
          "One step at a time.",
          "Let's collect gently.",
        ];
        _setComment(moveLines[_rng.nextInt(moveLines.length)]);
      }
    }
  }

  void _showWinDialog() {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (_) => AlertDialog(
        title: const Text(
          "Level complete",
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
          ),
        ),
        content: Text(
          questCompleted
              ? "You collected all drops and finished the quest!"
              : "You collected all drops.\n(Quest is optional.)",
          style: const TextStyle(
            color: AppColors.textDark,
            fontSize: 16,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _restart();
            },
            child: const Text(
              "Play again",
              style: TextStyle(
                color: AppColors.titletext,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text(
              "Close",
              style: TextStyle(
                color: AppColors.titletext,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _restart() {
    setState(() {
      nimiRow = 1;
      nimiCol = 0;
      comment = "Collect the drops";
      commentDrop = null;
      rippleKey = null;
      nimiScale = 1.0;
      barriers.clear();
    });

    _generateQuest();
    _spawnDrops();
  }

  // For holding joystick direction (optional)
  void _startHold(Dir dir) {
    _holdTimer?.cancel();
    _holdTimer = Timer.periodic(const Duration(milliseconds: 120), (_) {
      _tryMove(dir);
    });
  }

  void _stopHold() {
    _holdTimer?.cancel();
    _holdTimer = null;
  }

  @override
  Widget build(BuildContext context) {
    // Using your app theme colors (adjust if needed)
    const boardBg = AppColors.blue;
    const tileColor = AppColors.background;
    const tileBorder = AppColors.background;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Collect drops",
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
          ),
        ),
        actions: [
          // Optional: star counter (non-competitive)
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  Image.asset("assets/images/nimi_star.png", width: 20, height: 20),
                  const SizedBox(width: 4),
                  Text(
                    "$stars",
                    style: const TextStyle(
                      color: AppColors.titletext,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.titletext),
            onPressed: _restart,
            tooltip: "Restart",
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 10),

            // QUEST BAR
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.background,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.lighterblue),
                ),
                child: Row(
                  children: [
                    const Text(
                      "Quest: Collect ",
                      style: TextStyle(
                        color: AppColors.textDark,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      "$questTarget ",
                      style: const TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w600),
                    ),
                    Image.asset(dropImage(questType), width: 20, height: 20),
                    const Spacer(),
                    Text(
                      "$questProgress/$questTarget",
                      style: TextStyle(
                        color: questCompleted ? Colors.green : AppColors.textDark,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (questCompleted)
                      const Icon(Icons.check_circle, color: Colors.green, size: 20),
                  ],
                ),
              ),
            ),

            // BOARD
            Expanded(
              child: Center(
                child: AspectRatio(
                  aspectRatio: 1,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: boardBg,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: tileBorder),
                    ),
                    child: _BoardGrid(
                      rows: rows,
                      cols: cols,
                      tileColor: tileColor,
                      borderColor: tileBorder,
                      nimiRow: nimiRow,
                      nimiCol: nimiCol,
                      nimiScale: nimiScale,
                      drops: drops,
                      barriers: barriers,
                      rippleKey: rippleKey,
                      rippleToken: rippleToken,
                    ),
                  ),
                ),
              ),
            ),

            // COMMENT BAR
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.background,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.blue),
                ),
                child: Row(
                  children: [
                    Text(
                      comment,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppColors.textDark,
                          ),
                    ),
                    if (commentDrop != null) ...[
                      const SizedBox(width: 8),
                      Image.asset(dropImage(commentDrop!), width: 22, height: 22),
                    ],
                  ],
                ),
              ),
            ),

            // JOYSTICK
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: _DPad(
                onTap: _tryMove,
                onHoldStart: _startHold,
                onHoldEnd: _stopHold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

enum Dir { up, down, left, right }

enum DropType { calm, focus, energy }

String dropImage(DropType t) {
  switch (t) {
    case DropType.calm:   return "assets/images/nimi_water_drop.png";
    case DropType.focus:  return "assets/images/nimi_star.png";
    case DropType.energy: return "assets/images/nimi_leaf.png";
  }
}

class _BoardGrid extends StatelessWidget {
  const _BoardGrid({
    required this.rows,
    required this.cols,
    required this.tileColor,
    required this.borderColor,
    required this.nimiRow,
    required this.nimiCol,
    required this.nimiScale,
    required this.drops,
    required this.barriers,
    required this.rippleKey,
    required this.rippleToken,
  });

  final int rows;
  final int cols;
  final Color tileColor;
  final Color borderColor;

  final int nimiRow;
  final int nimiCol;
  final double nimiScale;

  final Map<String, DropType> drops;
  final Set<String> barriers;

  final String? rippleKey;
  final int rippleToken;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: cols,
        crossAxisSpacing: 6,
        mainAxisSpacing: 6,
      ),
      itemCount: rows * cols,
      itemBuilder: (_, i) {
        final r = i ~/ cols;
        final c = i % cols;
        final key = "$r,$c";

        final bool hasNimi = (r == nimiRow && c == nimiCol);
        final DropType? dropType = drops[key];
        final bool hasDrop = dropType != null;
        final bool showRipple = rippleKey == key;
        final bool isBarrier = barriers.contains(key);

        return Container(
          decoration: BoxDecoration(
            color: isBarrier ? const Color(0xFF8FA8B8) : tileColor,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: isBarrier ? const Color(0xFF6A8898) : borderColor),
          ),
          child: isBarrier
              ? const SizedBox()
              : Stack(
                  alignment: Alignment.center,
                  children: [
                    // Ripple behind everything
                    if (showRipple) _Ripple(token: rippleToken),

                    // Drop (type-based)
                    if (hasDrop)
                      Image.asset(dropImage(dropType!)),

                    // Nimi with subtle pop scale
                    if (hasNimi)
                      TweenAnimationBuilder<double>(
                        tween: Tween(begin: 1.0, end: nimiScale),
                        duration: const Duration(milliseconds: 140),
                        curve: Curves.easeOut,
                        builder: (_, s, child) =>
                            Transform.scale(scale: s, child: child),
                        child: Image.asset("assets/images/nimi_1.png"),
                      ),
                  ],
                ),
        );
      },
    );
  }
}

class _Ripple extends StatelessWidget {
  const _Ripple({required this.token});

  final int token;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      key: ValueKey(token),
      tween: Tween(begin: 0.0, end: 1.0),
      duration: const Duration(milliseconds: 360),
      curve: Curves.easeOut,
      builder: (_, t, __) {
        final double size = 8 + (28 * t);
        final double opacity = (1.0 - t) * 0.35; // calm, no flash
        return Opacity(
          opacity: opacity,
          child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFF7FB6CF), // soft blue rim
                width: 2,
              ),
            ),
          ),
        );
      },
    );
  }
}

class _DPad extends StatelessWidget {
  const _DPad({
    required this.onTap,
    required this.onHoldStart,
    required this.onHoldEnd,
  });

  final void Function(Dir dir) onTap;
  final void Function(Dir dir) onHoldStart;
  final VoidCallback onHoldEnd;

  Widget _btn(IconData icon, Dir dir) {
    return GestureDetector(
      onTap: () => onTap(dir),
      onLongPressStart: (_) => onHoldStart(dir),
      onLongPressEnd: (_) => onHoldEnd(),
      child: Container(
        width: 64,
        height: 64,
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.lighterblue),
        ),
        child: Icon(icon, color: AppColors.titletext),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.blue,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.lighterblue),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _btn(Icons.keyboard_arrow_up, Dir.up),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _btn(Icons.keyboard_arrow_left, Dir.left),
              const SizedBox(width: 80),
              _btn(Icons.keyboard_arrow_right, Dir.right),
            ],
          ),
          _btn(Icons.keyboard_arrow_down, Dir.down),
        ],
      ),
    );
  }
}

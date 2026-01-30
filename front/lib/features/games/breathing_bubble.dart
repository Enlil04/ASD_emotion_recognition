import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../../theme/app_colors.dart';

class BubbleBreathingGame extends StatefulWidget {
  const BubbleBreathingGame({Key? key}) : super(key: key);

  @override
  State<BubbleBreathingGame> createState() =>
      _BubbleBreathingGameState();
}

class _BubbleBreathingGameState
    extends State<BubbleBreathingGame>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  bool _isPlaying = false;
  int _breathCount = 0;
  String _currentPhase = 'Ready';

  // Customizable settings
  double _inhaleTime = 4.0;
  double _holdTime = 2.0;
  double _exhaleTime = 4.0;
  double _pauseTime = 2.0;
  bool _showFace = true;
  bool _showText = true;
  int _targetBreaths = 5;

  @override
  void initState() {
    super.initState();
    _initializeAnimation();
  }

  void _initializeAnimation() {
    final totalCycleTime = _inhaleTime + _holdTime + _exhaleTime + _pauseTime;

    _controller = AnimationController(
      duration: Duration(milliseconds: (totalCycleTime * 1000).toInt()),
      vsync: this,
    );

    _animation = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween<double>(begin: 0.5, end: 1.0)
            .chain(CurveTween(curve: Curves.easeInOut)),
        weight: _inhaleTime,
      ),
      TweenSequenceItem(
        tween: ConstantTween<double>(1.0),
        weight: _holdTime,
      ),
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.0, end: 0.5)
            .chain(CurveTween(curve: Curves.easeInOut)),
        weight: _exhaleTime,
      ),
      TweenSequenceItem(
        tween: ConstantTween<double>(0.5),
        weight: _pauseTime,
      ),
    ]).animate(_controller);

    _controller.addListener(() {
      if (!mounted) return;
      setState(() {
        final progress = _controller.value;
        final totalTime = _inhaleTime + _holdTime + _exhaleTime + _pauseTime;
        final currentTime = progress * totalTime;

        if (currentTime < _inhaleTime) {
          _currentPhase = 'Breathe In';
        } else if (currentTime < _inhaleTime + _holdTime) {
          _currentPhase = 'Hold';
        } else if (currentTime < _inhaleTime + _holdTime + _exhaleTime) {
          _currentPhase = 'Breathe Out';
        } else {
          _currentPhase = 'Rest';
        }
      });
    });

    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        setState(() {
          _breathCount++;
        });

        // Check if target reached
        if (_breathCount >= _targetBreaths) {
          _showCompletionDialog();
          _controller.reset();
          setState(() {
            _isPlaying = false;
            _currentPhase = 'Complete!';
          });
        } else {
          _controller.reset();
          if (_isPlaying) {
            _controller.forward();
          }
        }
      }
    });
  }

  void _showCompletionDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.background,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        title: Text(
          'Well Done!',
          style: TextStyle(
            color: AppColors.titletext,
            fontSize: 24,
            fontWeight: FontWeight.w600,
          ),
          textAlign: TextAlign.center,
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'You completed $_targetBreaths breaths!',
              style: TextStyle(
                color: AppColors.textDark,
                fontSize: 18,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              'Great job staying calm and focused.',
              style: TextStyle(
                color: AppColors.textDark,
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              _reset();
            },
            child: Text(
              'Continue',
              style: TextStyle(
                color: AppColors.titletext,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggleBreathing() {
    setState(() {
      _isPlaying = !_isPlaying;
      if (_isPlaying) {
        _controller.forward();
      } else {
        _controller.stop();
        _currentPhase = 'Paused';
      }
    });
  }

  void _reset() {
    setState(() {
      _controller.reset();
      _isPlaying = false;
      _breathCount = 0;
      _currentPhase = 'Ready';
    });
  }

  void _showSettings() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.background,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Padding(
          padding: const EdgeInsets.all(24.0),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Settings',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w600,
                    color: AppColors.titletext,
                  ),
                ),
                const SizedBox(height: 24),

                // Preset patterns
                Text(
                  'Breathing Pattern',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.titletext,
                  ),
                ),
                const SizedBox(height: 12),

                _buildPresetButton(
                  'Easy (3-1-3-1)',
                  'Good for children',
                  () {
                    setModalState(() {
                      _inhaleTime = 3.0;
                      _holdTime = 1.0;
                      _exhaleTime = 3.0;
                      _pauseTime = 1.0;
                    });
                  },
                  setModalState,
                ),

                _buildPresetButton(
                  'Medium (4-2-4-2)',
                  'Balanced breathing',
                  () {
                    setModalState(() {
                      _inhaleTime = 4.0;
                      _holdTime = 2.0;
                      _exhaleTime = 4.0;
                      _pauseTime = 2.0;
                    });
                  },
                  setModalState,
                ),

                _buildPresetButton(
                  'Calming (4-7-8)',
                  'Deep relaxation',
                  () {
                    setModalState(() {
                      _inhaleTime = 4.0;
                      _holdTime = 7.0;
                      _exhaleTime = 8.0;
                      _pauseTime = 2.0;
                    });
                  },
                  setModalState,
                ),

                const SizedBox(height: 24),

                // Target breaths slider
                Text(
                  'Target Breaths: $_targetBreaths',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: AppColors.titletext,
                  ),
                ),
                Slider(
                  value: _targetBreaths.toDouble(),
                  min: 3,
                  max: 20,
                  divisions: 17,
                  activeColor: AppColors.blue,
                  inactiveColor: AppColors.blue.withOpacity(0.3),
                  onChanged: (value) {
                    setModalState(() {
                      _targetBreaths = value.toInt();
                    });
                  },
                ),

                const SizedBox(height: 16),

                // Display options
                SwitchListTile(
                  title: Text(
                    'Show Face',
                    style: TextStyle(
                      color: AppColors.titletext,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  value: _showFace,
                  activeColor: AppColors.blue,
                  onChanged: (value) {
                    setModalState(() {
                      _showFace = value;
                    });
                  },
                ),

                SwitchListTile(
                  title: Text(
                    'Show Text Instructions',
                    style: TextStyle(
                      color: AppColors.titletext,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  value: _showText,
                  activeColor: AppColors.blue,
                  onChanged: (value) {
                    setModalState(() {
                      _showText = value;
                    });
                  },
                ),

                const SizedBox(height: 24),

                // Apply button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                        setState(() {
                          _reset();

                          final totalCycleTime = _inhaleTime + _holdTime + _exhaleTime + _pauseTime;
                          _controller.duration =
                              Duration(milliseconds: (totalCycleTime * 1000).toInt());

                          _animation = TweenSequence<double>([
                            TweenSequenceItem(
                              tween: Tween<double>(begin: 0.5, end: 1.0)
                                  .chain(CurveTween(curve: Curves.easeInOut)),
                              weight: _inhaleTime,
                            ),
                            TweenSequenceItem(
                              tween: ConstantTween<double>(1.0),
                              weight: _holdTime,
                            ),
                            TweenSequenceItem(
                              tween: Tween<double>(begin: 1.0, end: 0.5)
                                  .chain(CurveTween(curve: Curves.easeInOut)),
                              weight: _exhaleTime,
                            ),
                            TweenSequenceItem(
                              tween: ConstantTween<double>(0.5),
                              weight: _pauseTime,
                            ),
                          ]).animate(_controller);
                        });

                        Navigator.pop(context);
                      },

                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.blue,
                      foregroundColor: AppColors.titletext,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text(
                      'Apply Settings',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }



  Widget _buildPresetButton(
    String title,
    String subtitle,
    VoidCallback onTap,
    StateSetter setModalState,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.blue.withOpacity(0.2),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppColors.lighterblue,
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppColors.titletext,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 14,
                  color: AppColors.textDark,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Header with settings button
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Breathing Bubble',
                          style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w600,
                            color: AppColors.titletext,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Follow the bubble to breathe calmly',
                          style: TextStyle(
                            fontSize: 16,
                            color: AppColors.textDark,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: Icon(
                      Icons.settings_rounded,
                      color: AppColors.titletext,
                      size: 28,
                    ),
                    onPressed: _showSettings,
                  ),
                ],
              ),
            ),

            // Progress indicator
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppColors.blue.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'Breaths: $_breathCount / $_targetBreaths',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                        color: AppColors.titletext,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Main breathing bubble
            Expanded(
              child: Center(
                child: AnimatedBuilder(
                  animation: _animation,
                  builder: (context, child) {
                    return CustomPaint(
                      size: Size(
                        MediaQuery.of(context).size.width * 0.85,
                        MediaQuery.of(context).size.width * 0.85,
                      ),
                      painter: BreathingBubblePainter(
                        animationValue: _animation.value,
                        isPlaying: _isPlaying,
                        showFace: _showFace,
                        currentPhase: _currentPhase,
                      ),
                    );
                  },
                ),
              ),
            ),

            // Phase indicator
            if (_showText)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 20),
                child: Text(
                  _currentPhase,
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w600,
                    color: AppColors.titletext,
                  ),
                ),
              ),

            // Control buttons
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _buildButton(
                    icon: Icons.refresh_rounded,
                    label: 'Reset',
                    onPressed: _reset,
                    backgroundColor: AppColors.lighterblue,
                    isLarge: true,
                  ),
                  const SizedBox(width: 20),
                  _buildButton(
                    icon: _isPlaying
                        ? Icons.pause_rounded
                        : Icons.play_arrow_rounded,
                    label: _isPlaying ? 'Pause' : 'Start',
                    onPressed: _toggleBreathing,
                    backgroundColor: AppColors.blue,
                    isLarge: true,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
    required Color backgroundColor,
    bool isLarge = false,
  }) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: backgroundColor,
        foregroundColor: AppColors.titletext,
        padding: EdgeInsets.symmetric(
          horizontal: isLarge ? 30 : 24,
          vertical: isLarge ? 20 : 16,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(30),
        ),
        elevation: 2,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: isLarge ? 32 : 24),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              fontSize: isLarge ? 20 : 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class BreathingBubblePainter extends CustomPainter {
  final double animationValue;
  final bool isPlaying;
  final bool showFace;
  final String currentPhase;

  BreathingBubblePainter({
    required this.animationValue,
    required this.isPlaying,
    this.showFace = true,
    this.currentPhase = 'Ready',
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final baseRadius = size.width / 2;

    // Draw concentric circles
    for (int i = 3; i >= 1; i--) {
      final ringRadius = baseRadius * animationValue * (0.7 + (i * 0.15));
      final ringPaint = Paint()
        ..color = _getRingColor(i).withOpacity(0.15)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(center, ringRadius, ringPaint);
    }

    // Main bubble
    final bubbleRadius = baseRadius * animationValue * 0.65;

    final shadowPaint = Paint()
      ..color = AppColors.textDark.withOpacity(0.1)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 15);
    canvas.drawCircle(center + const Offset(0, 5), bubbleRadius, shadowPaint);

    final bubblePaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, bubbleRadius, bubblePaint);

    final outlinePaint = Paint()
      ..color = AppColors.lighterblue.withOpacity(0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawCircle(center, bubbleRadius, outlinePaint);

    // Draw face
    if (isPlaying && showFace) {
      _drawFace(canvas, center, bubbleRadius);
    }
  }

  Color _getRingColor(int index) {
    switch (index) {
      case 1:
        return AppColors.lighterblue;
      case 2:
        return AppColors.blue;
      case 3:
        return AppColors.blue.withOpacity(0.7);
      default:
        return AppColors.blue;
    }
  }

  void _drawFace(Canvas canvas, Offset center, double radius) {
    final facePaint = Paint()
      ..color = AppColors.titletext
      ..style = PaintingStyle.fill;

    final eyeRadius = radius * 0.08;
    final eyeY = center.dy - radius * 0.1;
    final eyeSpacing = radius * 0.25;

    // Calculate eye openness based on current breathing phase
    // Fixed calculation for proper phase synchronization
    double eyeOpenness;
    
    if (currentPhase == 'Breathe In') {
      // Inhaling: eyes slowly close (1.0 -> 0.0)
      // animationValue goes from 0.5 to 1.0 during inhale
      // Map this to eyeOpenness 1.0 -> 0.0
      eyeOpenness = 1.0 - ((animationValue - 0.5) / 0.5);
      eyeOpenness = eyeOpenness.clamp(0.0, 1.0);
    } else if (currentPhase == 'Hold') {
      // Holding breath: keep eyes closed
      eyeOpenness = 0.0;
    } else if (currentPhase == 'Breathe Out') {
      // Exhaling: eyes slowly open (0.0 -> 1.0)
      // animationValue goes from 1.0 back to 0.5 during exhale
      // Map this to eyeOpenness 0.0 -> 1.0
      eyeOpenness = (1.0 - animationValue) / 0.5;
      eyeOpenness = eyeOpenness.clamp(0.0, 1.0);
    } else if (currentPhase == 'Rest') {
      // Resting: keep eyes open
      eyeOpenness = 1.0;
    } else {
      // Ready/Paused: eyes open
      eyeOpenness = 1.0;
    }

    // Draw eyes with variable openness
    if (eyeOpenness > 0.3) {
      // Draw open eyes (oval shape)
      final currentEyeHeight = eyeRadius * 2 * eyeOpenness;
      
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(center.dx - eyeSpacing, eyeY),
          width: eyeRadius * 1.5,
          height: currentEyeHeight,
        ),
        facePaint,
      );

      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(center.dx + eyeSpacing, eyeY),
          width: eyeRadius * 1.5,
          height: currentEyeHeight,
        ),
        facePaint,
      );
    } else {
      // Draw closed/nearly closed eyes (curved lines)
      final eyePaint = Paint()
        ..color = AppColors.titletext
        ..style = PaintingStyle.stroke
        ..strokeWidth = radius * 0.04
        ..strokeCap = StrokeCap.round;

      final eyeCurve = eyeOpenness * 0.5;

      // Left eye (curved line)
      final leftEyePath = Path();
      leftEyePath.moveTo(center.dx - eyeSpacing - eyeRadius, eyeY);
      leftEyePath.quadraticBezierTo(
        center.dx - eyeSpacing,
        eyeY + eyeRadius * eyeCurve,
        center.dx - eyeSpacing + eyeRadius,
        eyeY,
      );
      canvas.drawPath(leftEyePath, eyePaint);

      // Right eye (curved line)
      final rightEyePath = Path();
      rightEyePath.moveTo(center.dx + eyeSpacing - eyeRadius, eyeY);
      rightEyePath.quadraticBezierTo(
        center.dx + eyeSpacing,
        eyeY + eyeRadius * eyeCurve,
        center.dx + eyeSpacing + eyeRadius,
        eyeY,
      );
      canvas.drawPath(rightEyePath, eyePaint);
    }

    // Draw consistent smile
    final smilePath = Path();
    final smileWidth = radius * 0.5;
    final smileHeight = radius * 0.15;
    final smileY = center.dy + radius * 0.15;

    smilePath.moveTo(center.dx - smileWidth / 2, smileY);
    smilePath.quadraticBezierTo(
      center.dx,
      smileY + smileHeight,
      center.dx + smileWidth / 2,
      smileY,
    );

    final smilePaint = Paint()
      ..color = AppColors.titletext
      ..style = PaintingStyle.stroke
      ..strokeWidth = radius * 0.06
      ..strokeCap = StrokeCap.round;

    canvas.drawPath(smilePath, smilePaint);
  }

  @override
  bool shouldRepaint(BreathingBubblePainter oldDelegate) {
    return oldDelegate.animationValue != animationValue ||
        oldDelegate.isPlaying != isPlaying ||
        oldDelegate.showFace != showFace ||
        oldDelegate.currentPhase != currentPhase;
  }
}

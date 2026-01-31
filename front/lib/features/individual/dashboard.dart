import 'dart:convert'; // Still needed for jsonDecode if doing manual parsing, but ApiService now handles the initial Decode.
import 'dart:math';
import 'package:flutter/material.dart';
// import 'package:http/http.dart' as http; // <--- REMOVED
import '../../theme/app_colors.dart';
import '../../services/api_service.dart'; // <--- ADD THIS (Adjust path to match your project structure)

class DashboardInsightsScreen extends StatefulWidget {
  const DashboardInsightsScreen({super.key});

  @override
  State<DashboardInsightsScreen> createState() => _DashboardInsightsScreenState();
}

class _DashboardInsightsScreenState extends State<DashboardInsightsScreen> {
  final List<String> emotions = const [
    "Happy",
    "Sad",
    "Anger",
    "Fear",
    "Surprise",
    "Disgust",
    "Neutral",
  ];

  String insightsEmotion = "Neutral";
  Map<String, List<double>> weeklyEmotionSeries = {};
  List<String> last7Days = const [];
  String dailyRecommendation = "";
  bool _loading = true;
  String? _loadError;

  String latestDetectedEmotion = "No emotion Detected";
  double latestConfidence = 0; 

  // URL removed: Using ApiService.baseUrl instead

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

Future<void> _loadDashboard() async {
  setState(() {
    _loading = true;
    _loadError = null;
  });

  try {
    // 1) Weekly aggregates
    final weeklyJson = await ApiService.fetchWeeklyEmotions("user_001");

    final days = (weeklyJson["days"] as List<dynamic>).map((e) => e.toString()).toList();
    final series = (weeklyJson["series"] as Map<String, dynamic>);

    final Map<String, List<double>> parsedSeries = {};
    for (final entry in series.entries) {
      final key = entry.key.toString();
      final raw = entry.value as List<dynamic>;
      parsedSeries[key] = raw.map((v) => (v as num).toDouble()).toList();
    }

    // 2) Daily recommendation
    final recJson = await ApiService.fetchDailyRecommendation("user_001");
    final recText = (recJson["recommendation"] ?? "").toString();

    // ✅ 3) Latest detected emotion (from emotion_logs)
    final latestJson = await ApiService.fetchLatestEmotion("user_001");
    final latestEmotion = (latestJson["emotion"] ?? "No emotion detected").toString();
    final latestConf = (latestJson["confidence"] as num?)?.toDouble() ?? 0.0;

    setState(() {
      last7Days = days;
      weeklyEmotionSeries = parsedSeries;
      dailyRecommendation = recText;

      // ✅ update the top "Latest detected" UI
      latestDetectedEmotion = latestEmotion;
      latestConfidence = latestConf;

      _loading = false;
    });
  } catch (e) {
    setState(() {
      _loadError = e.toString();
      _loading = false;
    });
  }
}

  @override
  Widget build(BuildContext context) {
    final weeklyData =
        weeklyEmotionSeries[insightsEmotion] ?? const [0, 0, 0, 0, 0, 0, 0];

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: AppColors.background,
        title: const Text(
          "Dashboard",
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          if (_loadError != null)
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: AppColors.blue.withOpacity(0.55),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.lighterblue),
              ),
              child: Text(
                "Dashboard data error: $_loadError",
                style: const TextStyle(color: AppColors.titletext, fontWeight: FontWeight.w600),
              ),
            ),
          
          _card(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      "Weekly mood diagram",
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppColors.titletext,
                      ),
                    ),
                    const Spacer(),
                    _emotionSelector(insightsEmotion),
                  ],
                ),
                const SizedBox(height: 12),

                SizedBox(
                  height: 190,
                  child: WeeklyMoodChart(values: weeklyData),
                ),

                const SizedBox(height: 14),

                _contextStrip(),

                const SizedBox(height: 14),

                _agenticRecommendationBlock(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ... (Rest of the file remains exactly the same: _contextStrip, _agenticRecommendationBlock, _emotionSelector, _card, WeeklyMoodChart)
  
  Widget _contextStrip() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.lighterblue),
      ),
      child: Row(
        children: [
          const CircleAvatar(
            radius: 16,
            backgroundColor: AppColors.blue,
            child: Icon(Icons.insights_rounded, size: 18, color: AppColors.titletext),
          ),
          const SizedBox(width: 10),
         Expanded(
              child: Text(
                latestDetectedEmotion == "No emotion detected" ||
                        latestDetectedEmotion.isEmpty
                    ? "Latest detected: No emotion detected"
                    : "Latest detected: $latestDetectedEmotion  •  ${latestConfidence.round()}% confidence",
                style: const TextStyle(
                  color: AppColors.textDark,
                  fontWeight: FontWeight.w600,
                ),
  ),

),

        ],
      ),
    );
  }

  Widget _agenticRecommendationBlock() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.lighterblue),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "Recommendation",
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.titletext,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.blue.withOpacity(0.55),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Text(
              (dailyRecommendation.isEmpty ? "Loading..." : dailyRecommendation),
              style: const TextStyle(
                color: AppColors.titletext,
                fontSize: 12.5,
                height: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),

          const SizedBox(height: 12),

  ],
      ),
    );
  }
  Widget _emotionSelector(String label) {
    return InkWell(
      onTap: _openEmotionPicker,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          children: [
            const CircleAvatar(
              radius: 12,
              backgroundColor: AppColors.lighterblue,
              child: Icon(Icons.expand_more, size: 16, color: AppColors.titletext),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: const TextStyle(
                color: AppColors.titletext,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _openEmotionPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) {
        return Container(
          margin: const EdgeInsets.fromLTRB(14, 0, 14, 14),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.background,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: AppColors.blue),
          ),
          child: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: emotions.map((e) {
              final selected = insightsEmotion == e;
              return ChoiceChip(
                label: Text(e),
                selected: selected,
                selectedColor: AppColors.lighterblue,
                backgroundColor: AppColors.blue.withOpacity(0.45),
                labelStyle: TextStyle(
                  color: AppColors.titletext,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                ),
                onSelected: (_) {
                  setState(() => insightsEmotion = e);
                  Navigator.pop(context);
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  Widget _card(Widget child) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.blue,
        borderRadius: BorderRadius.circular(22),
      ),
      child: child,
    );
  }
}

class WeeklyMoodChart extends StatelessWidget {
  final List<double> values; 
  const WeeklyMoodChart({super.key, required this.values});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _WeeklyMoodPainter(values),
      child: const SizedBox.expand(),
    );
  }
}

class _WeeklyMoodPainter extends CustomPainter {
  final List<double> values;
  _WeeklyMoodPainter(this.values);

  final List<String> days = const ["M", "T", "W", "T", "F", "S", "S"];

  @override
  void paint(Canvas canvas, Size size) {
    final barPaint = Paint()..color = AppColors.lighterblue;

    final gridPaint = Paint()
      ..color = AppColors.textDark.withOpacity(0.14)
      ..strokeWidth = 1;

    final textPainter = TextPainter(
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
    );

    const leftPadding = 10.0;
    const rightPadding = 10.0;
    const bottomPadding = 26.0;
    const topPadding = 8.0;

    final chartHeight = size.height - topPadding - bottomPadding;
    final chartWidth = size.width - leftPadding - rightPadding;

    for (int i = 0; i <= 3; i++) {
      final y = topPadding + (chartHeight / 3) * i;
      canvas.drawLine(
        Offset(leftPadding, y),
        Offset(size.width - rightPadding, y),
        gridPaint,
      );
    }

    final n = min(values.length, 7);
    final barWidth = chartWidth / (n * 1.6);
    final gap = barWidth * 0.6;

    for (int i = 0; i < n; i++) {
      final v = values[i].clamp(0.0, 1.0);
      final barHeight = chartHeight * v;

      final x = leftPadding + i * (barWidth + gap);
      final y = topPadding + (chartHeight - barHeight);

      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(x, y, barWidth, barHeight),
          const Radius.circular(10),
        ),
        barPaint,
      );

      final day = days[i];
      textPainter.text = TextSpan(
        text: day,
        style: const TextStyle(
          color: AppColors.titletext,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      );
      textPainter.layout(minWidth: barWidth, maxWidth: barWidth);
      textPainter.paint(
        canvas,
        Offset(x, topPadding + chartHeight + 6),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _WeeklyMoodPainter oldDelegate) => true;
}


// import 'dart:convert';
// import 'dart:math';
// import 'package:flutter/material.dart';
// import 'package:http/http.dart' as http;
// import '../../theme/app_colors.dart';

// class DashboardInsightsScreen extends StatefulWidget {
//   const DashboardInsightsScreen({super.key});

//   @override
//   State<DashboardInsightsScreen> createState() => _DashboardInsightsScreenState();
// }

// class _DashboardInsightsScreenState extends State<DashboardInsightsScreen> {
//   final List<String> emotions = const [
//     "Happy",
//     "Sad",
//     "Anger",
//     "Fear",
//     "Surprise",
//     "Disgust",
//     "Neutral",
//   ];

//   String insightsEmotion = "Neutral";
//   // Loaded from backend (SQLite aggregates)
//   Map<String, List<double>> weeklyEmotionSeries = {};
//   List<String> last7Days = const [];
//   String dailyRecommendation = "";
//   bool _loading = true;
//   String? _loadError;


//   /// Replace with your real latest detection state (tool/session memory).
//   String latestDetectedEmotion = "Neutral";
//   double latestConfidence = 0.62; // 0..1


//   // IMPORTANT: replace with your server IP (same one you use in ApiService)
//   // Android emulator: http://10.0.2.2:8000
//   static const String baseUrl = "http://10.60.165.50:8000";

//   @override
//   void initState() {
//     super.initState();
//     _loadDashboard();
//   }

//   Future<void> _loadDashboard() async {
//     setState(() {
//       _loading = true;
//       _loadError = null;
//     });

//     try {
//       // 1) Weekly aggregates (last 7 days)
//       final weeklyRes = await http.get(Uri.parse("$baseUrl/api/emotions/weekly?user_id=user_001"));
//       if (weeklyRes.statusCode != 200) {
//         throw Exception("Weekly endpoint failed: ${weeklyRes.statusCode}");
//       }
//       final weeklyJson = jsonDecode(weeklyRes.body) as Map<String, dynamic>;
//       final days = (weeklyJson["days"] as List<dynamic>).map((e) => e.toString()).toList();
//       final series = (weeklyJson["series"] as Map<String, dynamic>);

//       final Map<String, List<double>> parsedSeries = {};
//       for (final entry in series.entries) {
//         final key = entry.key.toString();
//         final raw = entry.value as List<dynamic>;
//         parsedSeries[key] = raw.map((v) => (v as num).toDouble()).toList();
//       }

//       // 2) Daily recommendation (generated by AgenticBrain)
//       final recRes = await http.get(Uri.parse("$baseUrl/api/recommendation/today?user_id=user_001"));
//       if (recRes.statusCode != 200) {
//         throw Exception("Recommendation endpoint failed: ${recRes.statusCode}");
//       }
//       final recJson = jsonDecode(recRes.body) as Map<String, dynamic>;
//       final recText = (recJson["recommendation"] ?? "").toString();

//       setState(() {
//         last7Days = days;
//         weeklyEmotionSeries = parsedSeries;
//         dailyRecommendation = recText;
//         _loading = false;
//       });
//     } catch (e) {
//       setState(() {
//         _loadError = e.toString();
//         _loading = false;
//       });
//     }
//   }

//   @override
//   Widget build(BuildContext context) {
//     final weeklyData =
//         weeklyEmotionSeries[insightsEmotion] ?? const [0, 0, 0, 0, 0, 0, 0];

//     return Scaffold(
//       backgroundColor: AppColors.background,
//       appBar: AppBar(
//         elevation: 0,
//         backgroundColor: AppColors.background,
//         title: const Text(
//           "Dashboard",
//           style: TextStyle(
//             color: AppColors.titletext,
//             fontWeight: FontWeight.bold,
//           ),
//         ),
        
//       ),
//       body: ListView(
//         padding: const EdgeInsets.all(18),
//         children: [
//           if (_loadError != null)
//             Container(
//               padding: const EdgeInsets.all(12),
//               margin: const EdgeInsets.only(bottom: 12),
//               decoration: BoxDecoration(
//                 color: AppColors.blue.withOpacity(0.55),
//                 borderRadius: BorderRadius.circular(14),
//                 border: Border.all(color: AppColors.lighterblue),
//               ),
//               child: Text(
//                 "Dashboard data error: $_loadError",
//                 style: const TextStyle(color: AppColors.titletext, fontWeight: FontWeight.w600),
//               ),
//             ),
          
//           _card(
//             Column(
//               crossAxisAlignment: CrossAxisAlignment.start,
//               children: [
//                 // Header row
//                 Row(
//                   children: [
//                     const Text(
//                       "Weekly mood diagram",
//                       style: TextStyle(
//                         fontSize: 16,
//                         fontWeight: FontWeight.bold,
//                         color: AppColors.titletext,
//                       ),
//                     ),
//                     const Spacer(),
//                     _emotionSelector(insightsEmotion),
//                   ],
//                 ),
//                 const SizedBox(height: 12),

//                 SizedBox(
//                   height: 190,
//                   child: WeeklyMoodChart(values: weeklyData),
//                 ),

//                 const SizedBox(height: 14),

//                 _contextStrip(),

//                 const SizedBox(height: 14),

//                 _agenticRecommendationBlock(),
//               ],
//             ),
//           ),
//         ],
//       ),
//     );
//   }

//   Widget _contextStrip() {
//     return Container(
//       padding: const EdgeInsets.all(12),
//       decoration: BoxDecoration(
//         color: AppColors.background,
//         borderRadius: BorderRadius.circular(18),
//         border: Border.all(color: AppColors.lighterblue),
//       ),
//       child: Row(
//         children: [
//           const CircleAvatar(
//             radius: 16,
//             backgroundColor: AppColors.blue,
//             child: Icon(Icons.insights_rounded, size: 18, color: AppColors.titletext),
//           ),
//           const SizedBox(width: 10),
//           Expanded(
//             child: Text(
//               "Latest detected: $latestDetectedEmotion  •  ${(latestConfidence * 100).round()}% confidence",
//               style: const TextStyle(
//                 color: AppColors.textDark,
//                 fontWeight: FontWeight.w600,
//               ),
//             ),
//           ),
//         ],
//       ),
//     );
//   }

//   Widget _agenticRecommendationBlock() {
//     return Container(
//       padding: const EdgeInsets.all(14),
//       decoration: BoxDecoration(
//         color: AppColors.background,
//         borderRadius: BorderRadius.circular(18),
//         border: Border.all(color: AppColors.lighterblue),
//       ),
//       child: Column(
//         crossAxisAlignment: CrossAxisAlignment.start,
//         children: [
//           const Text(
//             "Recommendation",
//             style: TextStyle(
//               fontSize: 15,
//               fontWeight: FontWeight.bold,
//               color: AppColors.titletext,
//             ),
//           ),
//           const SizedBox(height: 8),
//           Container(
//             width: double.infinity,
//             padding: const EdgeInsets.all(12),
//             decoration: BoxDecoration(
//               color: AppColors.blue.withOpacity(0.55),
//               borderRadius: BorderRadius.circular(14),
//             ),
//             child: Text(
//               (dailyRecommendation.isEmpty ? "Loading..." : dailyRecommendation),
//               style: const TextStyle(
//                 color: AppColors.titletext,
//                 fontSize: 12.5,
//                 height: 1.2,
//                 fontWeight: FontWeight.w600,
//               ),
//             ),
//           ),

//           const SizedBox(height: 12),

//   ],
//       ),
//     );
//   }
//   Widget _emotionSelector(String label) {
//     return InkWell(
//       onTap: _openEmotionPicker,
//       borderRadius: BorderRadius.circular(20),
//       child: Container(
//         padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
//         decoration: BoxDecoration(
//           color: AppColors.background,
//           borderRadius: BorderRadius.circular(20),
//         ),
//         child: Row(
//           children: [
//             const CircleAvatar(
//               radius: 12,
//               backgroundColor: AppColors.lighterblue,
//               child: Icon(Icons.expand_more, size: 16, color: AppColors.titletext),
//             ),
//             const SizedBox(width: 6),
//             Text(
//               label,
//               style: const TextStyle(
//                 color: AppColors.titletext,
//                 fontWeight: FontWeight.w700,
//               ),
//             ),
//           ],
//         ),
//       ),
//     );
//   }

//   void _openEmotionPicker() {
//     showModalBottomSheet(
//       context: context,
//       backgroundColor: Colors.transparent,
//       builder: (_) {
//         return Container(
//           margin: const EdgeInsets.fromLTRB(14, 0, 14, 14),
//           padding: const EdgeInsets.all(14),
//           decoration: BoxDecoration(
//             color: AppColors.background,
//             borderRadius: BorderRadius.circular(22),
//             border: Border.all(color: AppColors.blue),
//           ),
//           child: Wrap(
//             spacing: 10,
//             runSpacing: 10,
//             children: emotions.map((e) {
//               final selected = insightsEmotion == e;
//               return ChoiceChip(
//                 label: Text(e),
//                 selected: selected,
//                 selectedColor: AppColors.lighterblue,
//                 backgroundColor: AppColors.blue.withOpacity(0.45),
//                 labelStyle: TextStyle(
//                   color: AppColors.titletext,
//                   fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
//                 ),
//                 onSelected: (_) {
//                   setState(() => insightsEmotion = e);
//                   Navigator.pop(context);
//                 },
//               );
//             }).toList(),
//           ),
//         );
//       },
//     );
//   }

//   Widget _card(Widget child) {
//     return Container(
//       padding: const EdgeInsets.all(14),
//       decoration: BoxDecoration(
//         color: AppColors.blue,
//         borderRadius: BorderRadius.circular(22),
//       ),
//       child: child,
//     );
//   }
// }



// class WeeklyMoodChart extends StatelessWidget {
//   final List<double> values; // length 7 recommended
//   const WeeklyMoodChart({super.key, required this.values});

//   @override
//   Widget build(BuildContext context) {
//     return CustomPaint(
//       painter: _WeeklyMoodPainter(values),
//       child: const SizedBox.expand(),
//     );
//   }
// }

// class _WeeklyMoodPainter extends CustomPainter {
//   final List<double> values;
//   _WeeklyMoodPainter(this.values);

//   final List<String> days = const ["M", "T", "W", "T", "F", "S", "S"];

//   @override
//   void paint(Canvas canvas, Size size) {
//     final barPaint = Paint()..color = AppColors.lighterblue;

//     final gridPaint = Paint()
//       ..color = AppColors.textDark.withOpacity(0.14)
//       ..strokeWidth = 1;

//     final textPainter = TextPainter(
//       textAlign: TextAlign.center,
//       textDirection: TextDirection.ltr,
//     );

//     const leftPadding = 10.0;
//     const rightPadding = 10.0;
//     const bottomPadding = 26.0;
//     const topPadding = 8.0;

//     final chartHeight = size.height - topPadding - bottomPadding;
//     final chartWidth = size.width - leftPadding - rightPadding;

//     // Horizontal grid lines (0%, 33%, 66%, 100%)
//     for (int i = 0; i <= 3; i++) {
//       final y = topPadding + (chartHeight / 3) * i;
//       canvas.drawLine(
//         Offset(leftPadding, y),
//         Offset(size.width - rightPadding, y),
//         gridPaint,
//       );
//     }

//     final n = min(values.length, 7);
//     final barWidth = chartWidth / (n * 1.6);
//     final gap = barWidth * 0.6;

//     for (int i = 0; i < n; i++) {
//       final v = values[i].clamp(0.0, 1.0);
//       final barHeight = chartHeight * v;

//       final x = leftPadding + i * (barWidth + gap);
//       final y = topPadding + (chartHeight - barHeight);

//       // Bar
//       canvas.drawRRect(
//         RRect.fromRectAndRadius(
//           Rect.fromLTWH(x, y, barWidth, barHeight),
//           const Radius.circular(10),
//         ),
//         barPaint,
//       );

//       // Day label
//       final day = days[i];
//       textPainter.text = const TextSpan(
//         text: "",
//       );
//       textPainter.text = TextSpan(
//         text: day,
//         style: const TextStyle(
//           color: AppColors.titletext,
//           fontSize: 12,
//           fontWeight: FontWeight.w600,
//         ),
//       );
//       textPainter.layout(minWidth: barWidth, maxWidth: barWidth);
//       textPainter.paint(
//         canvas,
//         Offset(x, topPadding + chartHeight + 6),
//       );
//     }
//   }

//   @override
//   bool shouldRepaint(covariant _WeeklyMoodPainter oldDelegate) => true;
// }



// // import 'dart:math';
// // import 'package:flutter/material.dart';
// // import '../../theme/app_colors.dart';

// // class DashboardInsightsScreen extends StatefulWidget {
// //   const DashboardInsightsScreen({super.key});

// //   @override
// //   State<DashboardInsightsScreen> createState() => _DashboardInsightsScreenState();
// // }

// // class _DashboardInsightsScreenState extends State<DashboardInsightsScreen> {
// //   final List<String> emotions = const [
// //     "Happy",
// //     "Sad",
// //     "Angry",
// //     "Fear",
// //     "Surprise",
// //     "Disgust",
// //     "Neutral",
// //   ];

// //   String insightsEmotion = "Neutral";

// //   /// Demo data. Replace with your SQLite aggregation later.
// //   final Map<String, List<double>> weeklyEmotionSeries = {
// //     "Happy": [0.2, 0.3, 0.6, 0.5, 0.7, 0.4, 0.6],
// //     "Sad": [0.1, 0.2, 0.3, 0.2, 0.25, 0.3, 0.2],
// //     "Angry": [0.05, 0.1, 0.15, 0.08, 0.12, 0.1, 0.09],
// //     "Fear": [0.1, 0.05, 0.08, 0.12, 0.1, 0.06, 0.09],
// //     "Surprise": [0.15, 0.1, 0.12, 0.18, 0.2, 0.15, 0.1],
// //     "Disgust": [0.05, 0.04, 0.06, 0.05, 0.06, 0.05, 0.04],
// //     "Neutral": [0.35, 0.4, 0.25, 0.35, 0.25, 0.45, 0.3],
// //   };

// //   /// Replace with your real latest detection state (tool/session memory).
// //   String latestDetectedEmotion = "Neutral";
// //   double latestConfidence = 0.62; // 0..1

// //   @override
// //   Widget build(BuildContext context) {
// //     final weeklyData =
// //         weeklyEmotionSeries[insightsEmotion] ?? const [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2];

// //     return Scaffold(
// //       backgroundColor: AppColors.background,
// //       appBar: AppBar(
// //         elevation: 0,
// //         backgroundColor: AppColors.background,
// //         title: const Text(
// //           "Dashboard",
// //           style: TextStyle(
// //             color: AppColors.titletext,
// //             fontWeight: FontWeight.bold,
// //           ),
// //         ),
        
// //       ),
// //       body: ListView(
// //         padding: const EdgeInsets.all(18),
// //         children: [
// //           _card(
// //             Column(
// //               crossAxisAlignment: CrossAxisAlignment.start,
// //               children: [
// //                 // Header row
// //                 Row(
// //                   children: [
// //                     const Text(
// //                       "Weekly mood diagram",
// //                       style: TextStyle(
// //                         fontSize: 16,
// //                         fontWeight: FontWeight.bold,
// //                         color: AppColors.titletext,
// //                       ),
// //                     ),
// //                     const Spacer(),
// //                     _emotionSelector(insightsEmotion),
// //                   ],
// //                 ),
// //                 const SizedBox(height: 12),

// //                 SizedBox(
// //                   height: 190,
// //                   child: WeeklyMoodChart(values: weeklyData),
// //                 ),

// //                 const SizedBox(height: 14),

// //                 _contextStrip(),

// //                 const SizedBox(height: 14),

// //                 _agenticRecommendationBlock(),
// //               ],
// //             ),
// //           ),
// //         ],
// //       ),
// //     );
// //   }

// //   Widget _contextStrip() {
// //     return Container(
// //       padding: const EdgeInsets.all(12),
// //       decoration: BoxDecoration(
// //         color: AppColors.background,
// //         borderRadius: BorderRadius.circular(18),
// //         border: Border.all(color: AppColors.lighterblue),
// //       ),
// //       child: Row(
// //         children: [
// //           const CircleAvatar(
// //             radius: 16,
// //             backgroundColor: AppColors.blue,
// //             child: Icon(Icons.insights_rounded, size: 18, color: AppColors.titletext),
// //           ),
// //           const SizedBox(width: 10),
// //           Expanded(
// //             child: Text(
// //               "Latest detected: $latestDetectedEmotion  •  ${(latestConfidence * 100).round()}% confidence",
// //               style: const TextStyle(
// //                 color: AppColors.textDark,
// //                 fontWeight: FontWeight.w600,
// //               ),
// //             ),
// //           ),
// //         ],
// //       ),
// //     );
// //   }

// //   Widget _agenticRecommendationBlock() {
// //     return Container(
// //       padding: const EdgeInsets.all(14),
// //       decoration: BoxDecoration(
// //         color: AppColors.background,
// //         borderRadius: BorderRadius.circular(18),
// //         border: Border.all(color: AppColors.lighterblue),
// //       ),
// //       child: Column(
// //         crossAxisAlignment: CrossAxisAlignment.start,
// //         children: [
// //           const Text(
// //             "Recommendation",
// //             style: TextStyle(
// //               fontSize: 15,
// //               fontWeight: FontWeight.bold,
// //               color: AppColors.titletext,
// //             ),
// //           ),
// //           const SizedBox(height: 8),
// //           Container(
// //             width: double.infinity,
// //             padding: const EdgeInsets.all(12),
// //             decoration: BoxDecoration(
// //               color: AppColors.blue.withOpacity(0.55),
// //               borderRadius: BorderRadius.circular(14),
// //             ),
// //             child: Text(
// //              "Something",
// //               style: const TextStyle(
// //                 color: AppColors.titletext,
// //                 fontSize: 12.5,
// //                 height: 1.2,
// //                 fontWeight: FontWeight.w600,
// //               ),
// //             ),
// //           ),

// //           const SizedBox(height: 12),

// //   ],
// //       ),
// //     );
// //   }
// //   Widget _emotionSelector(String label) {
// //     return InkWell(
// //       onTap: _openEmotionPicker,
// //       borderRadius: BorderRadius.circular(20),
// //       child: Container(
// //         padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
// //         decoration: BoxDecoration(
// //           color: AppColors.background,
// //           borderRadius: BorderRadius.circular(20),
// //         ),
// //         child: Row(
// //           children: [
// //             const CircleAvatar(
// //               radius: 12,
// //               backgroundColor: AppColors.lighterblue,
// //               child: Icon(Icons.expand_more, size: 16, color: AppColors.titletext),
// //             ),
// //             const SizedBox(width: 6),
// //             Text(
// //               label,
// //               style: const TextStyle(
// //                 color: AppColors.titletext,
// //                 fontWeight: FontWeight.w700,
// //               ),
// //             ),
// //           ],
// //         ),
// //       ),
// //     );
// //   }

// //   void _openEmotionPicker() {
// //     showModalBottomSheet(
// //       context: context,
// //       backgroundColor: Colors.transparent,
// //       builder: (_) {
// //         return Container(
// //           margin: const EdgeInsets.fromLTRB(14, 0, 14, 14),
// //           padding: const EdgeInsets.all(14),
// //           decoration: BoxDecoration(
// //             color: AppColors.background,
// //             borderRadius: BorderRadius.circular(22),
// //             border: Border.all(color: AppColors.blue),
// //           ),
// //           child: Wrap(
// //             spacing: 10,
// //             runSpacing: 10,
// //             children: emotions.map((e) {
// //               final selected = insightsEmotion == e;
// //               return ChoiceChip(
// //                 label: Text(e),
// //                 selected: selected,
// //                 selectedColor: AppColors.lighterblue,
// //                 backgroundColor: AppColors.blue.withOpacity(0.45),
// //                 labelStyle: TextStyle(
// //                   color: AppColors.titletext,
// //                   fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
// //                 ),
// //                 onSelected: (_) {
// //                   setState(() => insightsEmotion = e);
// //                   Navigator.pop(context);
// //                 },
// //               );
// //             }).toList(),
// //           ),
// //         );
// //       },
// //     );
// //   }

// //   Widget _card(Widget child) {
// //     return Container(
// //       padding: const EdgeInsets.all(14),
// //       decoration: BoxDecoration(
// //         color: AppColors.blue,
// //         borderRadius: BorderRadius.circular(22),
// //       ),
// //       child: child,
// //     );
// //   }
// // }



// // class WeeklyMoodChart extends StatelessWidget {
// //   final List<double> values; // length 7 recommended
// //   const WeeklyMoodChart({super.key, required this.values});

// //   @override
// //   Widget build(BuildContext context) {
// //     return CustomPaint(
// //       painter: _WeeklyMoodPainter(values),
// //       child: const SizedBox.expand(),
// //     );
// //   }
// // }

// // class _WeeklyMoodPainter extends CustomPainter {
// //   final List<double> values;
// //   _WeeklyMoodPainter(this.values);

// //   final List<String> days = const ["M", "T", "W", "T", "F", "S", "S"];

// //   @override
// //   void paint(Canvas canvas, Size size) {
// //     final barPaint = Paint()..color = AppColors.lighterblue;

// //     final gridPaint = Paint()
// //       ..color = AppColors.textDark.withOpacity(0.14)
// //       ..strokeWidth = 1;

// //     final textPainter = TextPainter(
// //       textAlign: TextAlign.center,
// //       textDirection: TextDirection.ltr,
// //     );

// //     const leftPadding = 10.0;
// //     const rightPadding = 10.0;
// //     const bottomPadding = 26.0;
// //     const topPadding = 8.0;

// //     final chartHeight = size.height - topPadding - bottomPadding;
// //     final chartWidth = size.width - leftPadding - rightPadding;

// //     // Horizontal grid lines (0%, 33%, 66%, 100%)
// //     for (int i = 0; i <= 3; i++) {
// //       final y = topPadding + (chartHeight / 3) * i;
// //       canvas.drawLine(
// //         Offset(leftPadding, y),
// //         Offset(size.width - rightPadding, y),
// //         gridPaint,
// //       );
// //     }

// //     final n = min(values.length, 7);
// //     final barWidth = chartWidth / (n * 1.6);
// //     final gap = barWidth * 0.6;

// //     for (int i = 0; i < n; i++) {
// //       final v = values[i].clamp(0.0, 1.0);
// //       final barHeight = chartHeight * v;

// //       final x = leftPadding + i * (barWidth + gap);
// //       final y = topPadding + (chartHeight - barHeight);

// //       // Bar
// //       canvas.drawRRect(
// //         RRect.fromRectAndRadius(
// //           Rect.fromLTWH(x, y, barWidth, barHeight),
// //           const Radius.circular(10),
// //         ),
// //         barPaint,
// //       );

// //       // Day label
// //       final day = days[i];
// //       textPainter.text = const TextSpan(
// //         text: "",
// //       );
// //       textPainter.text = TextSpan(
// //         text: day,
// //         style: const TextStyle(
// //           color: AppColors.titletext,
// //           fontSize: 12,
// //           fontWeight: FontWeight.w600,
// //         ),
// //       );
// //       textPainter.layout(minWidth: barWidth, maxWidth: barWidth);
// //       textPainter.paint(
// //         canvas,
// //         Offset(x, topPadding + chartHeight + 6),
// //       );
// //     }
// //   }

// //   @override
// //   bool shouldRepaint(covariant _WeeklyMoodPainter oldDelegate) => true;
// // }

import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';
// CHANGE THIS IMPORT to match where you put the api_service.dart file
import '/services/api_service.dart'; 

class NimiScreen extends StatefulWidget {
  const NimiScreen({super.key});

  @override
  State<NimiScreen> createState() => _NimiScreenState();
}

class _NimiScreenState extends State<NimiScreen> {
  // 1. Controllers for Input and Scrolling
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  List<Chats> chats = [
    Chats(text: "What's on your mind?", time: "10:30 AM", isUser: false),
  ];

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  // 2. Logic to Send Message to Python Backend
  void _handleSend() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    // A. Update UI immediately (Optimistic UI)
    _textController.clear();
    setState(() {
      chats.add(Chats(
        text: text,
        time: _getCurrentTime(),
        isUser: true,
      ));
    });
    _scrollToBottom();

    // B. Send to Python API
    String response = await ApiService.sendMessage(text);

    // C. Update UI with Agent Response
    if (mounted) {
      setState(() {
        chats.add(Chats(
          text: response,
          time: _getCurrentTime(),
          isUser: false,
        ));
      });
      _scrollToBottom();
    }
  }

  String _getCurrentTime() {
    final now = DateTime.now();
    return "${now.hour}:${now.minute.toString().padLeft(2, '0')}";
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.blue.withOpacity(0.08),
      appBar: _builderAppBar(),
      body: Container(
        padding: const EdgeInsets.symmetric(horizontal: 15.0, vertical: 0.0),
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scrollController, // Attach ScrollController
                itemCount: chats.length,
                itemBuilder: (context, index) {
                  return chatBubble(chats[index]);
                },
              ),
            ),
            _builderInputArea()
          ],
        ),
      ),
    );
  }

  PreferredSizeWidget _builderAppBar() {
    return AppBar(
      backgroundColor: AppColors.background,
      toolbarHeight: 80,
      elevation: 0,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Nimi",
            style: TextStyle(
              color: AppColors.titletext,
              fontWeight: FontWeight.w500,
              fontSize: 20.0,
            ),
          ),
          const SizedBox(height: 10.0),
          Text(
            "Your personal companion",
            style: TextStyle(
              color: AppColors.textDark.withOpacity(0.6),
              fontSize: 14.0,
            ),
          )
        ],
      ),
    );
  }

  Widget chatBubble(Chats chat) {
    return Padding(
      padding: const EdgeInsets.all(15.0),
      child: Column(
        crossAxisAlignment:
            chat.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
            decoration: BoxDecoration(
              color: AppColors.lighterblue,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(15.0),
                topRight: const Radius.circular(15.0),
                bottomLeft: chat.isUser
                    ? const Radius.circular(15.0)
                    : const Radius.circular(0.0),
                bottomRight: chat.isUser
                    ? const Radius.circular(0.0)
                    : const Radius.circular(15.0),
              ),
            ),
            child: Text(
              chat.text,
              style: TextStyle(
                color: AppColors.background,
                fontSize: 16.0,
                height: 1.4,
              ),
            ),
          ),
          const SizedBox(height: 5),
          Text(
            chat.time,
            style: TextStyle(color: AppColors.textDark, fontSize: 12),
          )
        ],
      ),
    );
  }

  Widget _builderInputArea() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 30.0, vertical: 10.0),
      child: Row(
        children: [
          // Mic Button
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.lighterblue),
              borderRadius: BorderRadius.circular(10.0),
            ),
            child: IconButton(
              onPressed: () {
                // Future: Add speech-to-text logic here
              },
              icon: Icon(Icons.mic_none, color: AppColors.textDark),
            ),
          ),
          const SizedBox(width: 10.0),

          // Text Field
          Expanded(
            child: TextField(
              controller: _textController, // Connects to logic
              decoration: InputDecoration(
                hintText: "Chat with Nimi",
                hintStyle: TextStyle(
                  color: AppColors.textDark,
                ),
                filled: true,
                fillColor: AppColors.background,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(color: AppColors.lighterblue),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(color: AppColors.lighterblue),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12.0),

          // Send Button
          Container(
            decoration: BoxDecoration(
              color: AppColors.lighterblue,
              borderRadius: BorderRadius.circular(10.0),
            ),
            child: IconButton(
              onPressed: _handleSend, // Triggers the Python API call
              icon: Icon(
                Icons.send_rounded,
                color: AppColors.background,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Chat Model Class
class Chats {
  String text;
  String time;
  bool isUser;

  Chats({required this.text, required this.time, required this.isUser});
}

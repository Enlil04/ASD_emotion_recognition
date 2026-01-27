import 'package:flutter/material.dart';
import 'package:flutter_application_1/theme/app_colors.dart';
import '/services/api_service.dart';

class NimiScreen extends StatefulWidget {
  const NimiScreen({super.key});

  @override
  State<NimiScreen> createState() => _NimiScreenState();
}

class _NimiScreenState extends State<NimiScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  bool _isTyping = false;

  // 1. STATIC MEMORY: This list lives "outside" the screen.
  // We initialize it empty so we can set the dynamic time later.
  static List<Chats> chats = [];

  @override
  void initState() {
    super.initState();
    // 2. DYNAMIC START TIME
    // Only add the welcome message if the list is completely empty.
    if (chats.isEmpty) {
      chats.add(Chats(
        text: "What's on your mind?", 
        time: _getCurrentTime(), 
        isUser: false
      ));
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleSend() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    _textController.clear();
    
    // A. Add User Message
    setState(() {
      chats.add(Chats(text: text, time: _getCurrentTime(), isUser: true));
      _isTyping = true; 
    });
    _scrollToBottom();

    try {
      // B. Send to Python
      // We use a try-catch block so the app doesn't crash if server is down
      String response = await ApiService.sendMessage(text);

      // C. SAVE TO MEMORY (CRITICAL FIX)
      // We add the message to the static list IMMEDIATELY.
      // This happens even if you have navigated away to another tab!
      chats.add(Chats(
        text: response, 
        time: _getCurrentTime(), 
        isUser: false
      ));

      // D. Update UI (Only if you are still looking at the screen)
      if (mounted) {
        setState(() {
          _isTyping = false; 
        });
        _scrollToBottom();
      } else {
        // If you left the screen, we just turn off the typing flag silently
        _isTyping = false; 
      }

    } catch (e) {
      // Handle server error gracefully
      if (mounted) {
        setState(() {
          _isTyping = false;
          chats.add(Chats(text: "Server error: Is Python running?", time: _getCurrentTime(), isUser: false));
        });
      }
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
                controller: _scrollController,
                itemCount: chats.length + (_isTyping ? 1 : 0),
                itemBuilder: (context, index) {
                  if (_isTyping && index == chats.length) {
                    return _buildLoadingBubble();
                  }
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

  Widget _buildLoadingBubble() {
    return Padding(
      padding: const EdgeInsets.all(15.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
            decoration: BoxDecoration(
              color: AppColors.lighterblue,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(15.0),
                topRight: Radius.circular(15.0),
                bottomLeft: Radius.circular(0.0),
                bottomRight: Radius.circular(15.0),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 15, height: 15,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.background),
                ),
                const SizedBox(width: 10),
                Text("Thinking...", style: TextStyle(color: AppColors.background, fontSize: 14.0, fontStyle: FontStyle.italic)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget chatBubble(Chats chat) {
    return Padding(
      padding: const EdgeInsets.all(15.0),
      child: Column(
        crossAxisAlignment: chat.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
            decoration: BoxDecoration(
              color: AppColors.lighterblue,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(15.0),
                topRight: const Radius.circular(15.0),
                bottomLeft: chat.isUser ? const Radius.circular(15.0) : const Radius.circular(0.0),
                bottomRight: chat.isUser ? const Radius.circular(0.0) : const Radius.circular(15.0),
              ),
            ),
            child: Text(
              chat.text,
              style: TextStyle(color: AppColors.background, fontSize: 16.0, height: 1.4),
            ),
          ),
          const SizedBox(height: 5),
          Text(chat.time, style: TextStyle(color: AppColors.textDark, fontSize: 12))
        ],
      ),
    );
  }

  Widget _builderInputArea() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 30.0, vertical: 10.0),
      child: Row(
        children: [
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.lighterblue),
              borderRadius: BorderRadius.circular(10.0),
            ),
            child: IconButton(
              onPressed: () {},
              icon: Icon(Icons.mic_none, color: AppColors.textDark),
            ),
          ),
          const SizedBox(width: 10.0),
          Expanded(
            child: TextField(
              controller: _textController,
              decoration: InputDecoration(
                hintText: "Chat with Nimi",
                hintStyle: TextStyle(color: AppColors.textDark),
                filled: true,
                fillColor: AppColors.background,
                contentPadding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10.0), borderSide: BorderSide(color: AppColors.lighterblue)),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10.0), borderSide: BorderSide(color: AppColors.lighterblue)),
              ),
            ),
          ),
          const SizedBox(width: 12.0),
          Container(
            decoration: BoxDecoration(color: AppColors.lighterblue, borderRadius: BorderRadius.circular(10.0)),
            child: IconButton(
              onPressed: _handleSend,
              icon: Icon(Icons.send_rounded, color: AppColors.background),
            ),
          ),
        ],
      ),
    );
  }
}

class Chats {
  String text;
  String time;
  bool isUser;
  Chats({required this.text, required this.time, required this.isUser});
}
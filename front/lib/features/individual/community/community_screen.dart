import 'package:flutter/material.dart';
import '../../../theme/app_colors.dart';
import 'communitygames.dart';
import 'package:flutter_application_1/user_role.dart';

// NOTE: adjust this import path if your ApiService lives elsewhere in your project.
import '../../../services/api_service.dart';

class CommunityScreen extends StatefulWidget {
  const CommunityScreen({super.key, required this.userRole});
  final UserRole userRole;

  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  static const String _currentUserId = "user_001";

  final TextEditingController _searchCtrl = TextEditingController();

  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _allPosts = [];
  List<Map<String, dynamic>> _filteredPosts = [];

  @override
  void initState() {
    super.initState();
    _loadFeed();
    _searchCtrl.addListener(_applySearch);
  }

  @override
  void dispose() {
    _searchCtrl.removeListener(_applySearch);
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadFeed() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final res = await ApiService.fetchCommunityPosts(
        limit: 50,
        offset: 0,
      );

      final items = (res["items"] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .toList();

      setState(() {
        _allPosts = items;
        _filteredPosts = items;
        _loading = false;
      });

      _applySearch();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
        _allPosts = [];
        _filteredPosts = [];
      });
    }
  }

  void _applySearch() {
    final q = _searchCtrl.text.trim().toLowerCase();
    if (q.isEmpty) {
      setState(() => _filteredPosts = _allPosts);
      return;
    }

    setState(() {
      _filteredPosts = _allPosts.where((p) {
        final content = (p["content"] ?? "").toString().toLowerCase();
        final author = ((p["author"]?["name"]) ?? (p["author"]?["username"]) ?? "")
            .toString()
            .toLowerCase();
        return content.contains(q) || author.contains(q);
      }).toList();
    });
  }

  String _relativeTime(num? unixSeconds) {
    if (unixSeconds == null) return "";
    final dt = DateTime.fromMillisecondsSinceEpoch((unixSeconds * 1000).toInt());
    final diff = DateTime.now().difference(dt);

    if (diff.inSeconds < 60) return "just now";
    if (diff.inMinutes < 60) return "${diff.inMinutes} min ago";
    if (diff.inHours < 24) return "${diff.inHours} hours ago";
    if (diff.inDays < 7) return "${diff.inDays} days ago";
    final weeks = (diff.inDays / 7).floor();
    return "$weeks weeks ago";
  }

  Future<void> _openCreatePostSheet() async {
    final controller = TextEditingController();
    final created = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.background,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        final bottomInset = MediaQuery.of(ctx).viewInsets.bottom;
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 14,
            bottom: bottomInset + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "New post",
                style: TextStyle(
                  color: AppColors.titletext,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                minLines: 3,
                maxLines: 8,
                decoration: InputDecoration(
                  hintText: "Share something…",
                  hintStyle: TextStyle(color: AppColors.textDark.withOpacity(0.5)),
                  filled: true,
                  fillColor: AppColors.blue.withOpacity(0.18),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.lighterblue,
                        side: BorderSide(color: AppColors.lighterblue.withOpacity(0.5)),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      child: const Text("Cancel"),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () async {
                        final content = controller.text.trim();
                        if (content.isEmpty) return;

                        try {
                          await ApiService.createCommunityPost(
                            content: content,
                          );
                          if (mounted) Navigator.pop(ctx, true);
                        } catch (_) {
                          // keep sheet open
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.lighterblue,
                        foregroundColor: AppColors.background,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      child: const Text("Post"),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );

    if (created == true) {
      await _loadFeed();
    }
  }

  Future<void> _openPostDetail(Map<String, dynamic> post) async {
    final res = await Navigator.push<Map<String, dynamic>?>(
      context,
      MaterialPageRoute(
        builder: (_) => CommunityPostDetailScreen(
          post: post,
          currentUserId: _currentUserId,
        ),
      ),
    );

    // If detail screen returns updated counters, update feed without full reload.
    if (res != null) {
      final postId = post["id"];
      final idx = _allPosts.indexWhere((p) => p["id"] == postId);
      if (idx != -1) {
        setState(() {
          _allPosts[idx]["likes"] = res["likes"] ?? _allPosts[idx]["likes"];
          _allPosts[idx]["comments"] = res["comments"] ?? _allPosts[idx]["comments"];
          _allPosts[idx]["liked_by_me"] = res["liked_by_me"] ?? _allPosts[idx]["liked_by_me"];
        });
        _applySearch();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Community',
          style: TextStyle(
            color: AppColors.titletext,
            fontWeight: FontWeight.w500,
            fontSize: 20,
          ),
        ),
        backgroundColor: AppColors.background,
        elevation: 0,
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.sports_esports_outlined, color: AppColors.lighterblue),
            onPressed: () {

                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const CommunityGamesScreen()),
                );
              // if (widget.userRole != UserRole.guardian) {
              //   Navigator.push(
              //     context,
              //     MaterialPageRoute(builder: (context) => const CommunityGamesScreen()),
              //   );
              // }
            },
          ),
          const SizedBox(width: 6),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.lighterblue,
        onPressed: _openCreatePostSheet,
        child: const Icon(Icons.add, color: AppColors.background),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 10),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: "Search topics...",
                  hintStyle: const TextStyle(color: AppColors.lighterblue),
                  prefixIcon: const Icon(Icons.search, color: AppColors.blue),
                  filled: true,
                  fillColor: AppColors.blue.withOpacity(0.18),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _loadFeed,
                child: _buildBody(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return ListView(
        padding: const EdgeInsets.all(20),
        children: const [
          SizedBox(height: 40),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    if (_error != null) {
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const SizedBox(height: 30),
          const Text(
            "Couldn’t load community feed.",
            style: TextStyle(
              color: AppColors.textDark,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _error!,
            style: TextStyle(color: AppColors.textDark.withOpacity(0.6)),
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _loadFeed,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.lighterblue,
              foregroundColor: AppColors.background,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            child: const Text("Retry"),
          ),
        ],
      );
    }

    if (_filteredPosts.isEmpty) {
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const SizedBox(height: 30),
          Text(
            _searchCtrl.text.trim().isEmpty
                ? "No posts yet. Be the first to post."
                : "No results for \"${_searchCtrl.text.trim()}\"",
            style: TextStyle(color: AppColors.textDark.withOpacity(0.75)),
          ),
          const SizedBox(height: 12),
          const CommunityPostCard(
            author: "Mindfulness Coach",
            time: "2 hours ago",
            content:
                "Reminder 🌱\n\nTake a slow breath in through your nose, hold for 4 seconds, and gently release.\n\nYou’re doing better than you think.",
            likes: 24,
            comments: 5,
          ),
        ],
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(20, 6, 20, 20),
      itemCount: _filteredPosts.length,
      itemBuilder: (context, index) {
        final p = _filteredPosts[index];
        final author = p["author"] as Map<String, dynamic>? ?? {};
        final authorName = (author["name"] ?? author["username"] ?? "Unknown").toString();

        return CommunityPostCard(
          author: authorName,
          time: _relativeTime(p["date_created"] as num?),
          content: (p["content"] ?? "").toString(),
          likes: (p["likes"] ?? 0) as int,
          comments: (p["comments"] ?? 0) as int,
          likedByMe: (p["liked_by_me"] ?? false) as bool,
          onCardTap: () => _openPostDetail(p),
          onCommentTap: () => _openPostDetail(p),
          onLikeTap: () async {
            final postId = (p["id"] ?? 0) as int;
            final liked = (p["liked_by_me"] ?? false) as bool;

            // Optimistic UI
            setState(() {
              p["liked_by_me"] = !liked;
              p["likes"] = (p["likes"] ?? 0) + (liked ? -1 : 1);
            });

            try {
              if (!liked) {
                final res = await ApiService.likePost(postId: postId);
                p["likes"] = res["likes"] ?? p["likes"];
              } else {
                final res = await ApiService.unlikePost(postId: postId);
                p["likes"] = res["likes"] ?? p["likes"];
              }
              if (mounted) setState(() {});
            } catch (_) {
              // rollback if failed
              setState(() {
                p["liked_by_me"] = liked;
                p["likes"] = (p["likes"] ?? 0) + (liked ? 1 : -1);
              });
            }
          },
        );
      },
    );
  }
}

class CommunityPostCard extends StatelessWidget {
  final String author;
  final String time;
  final String content;
  final int likes;
  final int comments;

  final bool likedByMe;
  final VoidCallback? onLikeTap;
  final VoidCallback? onCommentTap;
  final VoidCallback? onCardTap;

  const CommunityPostCard({
    super.key,
    required this.author,
    required this.time,
    required this.content,
    required this.likes,
    required this.comments,
    this.likedByMe = false,
    this.onLikeTap,
    this.onCommentTap,
    this.onCardTap,
  });

  @override
  Widget build(BuildContext context) {
    final firstLetter = author.isNotEmpty ? author[0].toUpperCase() : "?";

    return InkWell(
      onTap: onCardTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.blue.withOpacity(0.18),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 18,
              offset: const Offset(0, 8),
            )
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundColor: AppColors.lighterblue.withOpacity(0.35),
                  child: Text(
                    firstLetter,
                    style: const TextStyle(
                      color: AppColors.titletext,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        author,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.titletext,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        time,
                        style: TextStyle(
                          color: AppColors.textDark.withOpacity(0.55),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              content,
              style: const TextStyle(
                color: AppColors.textDark,
                fontSize: 14,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                InkWell(
                  onTap: onLikeTap,
                  borderRadius: BorderRadius.circular(20),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Row(
                      children: [
                        Icon(
                          likedByMe ? Icons.favorite : Icons.favorite_border,
                          size: 18,
                          color: AppColors.lighterblue,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          "$likes",
                          style: const TextStyle(color: AppColors.textDark),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                InkWell(
                  onTap: onCommentTap,
                  borderRadius: BorderRadius.circular(20),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Row(
                      children: [
                        Icon(
                          Icons.chat_bubble_outline,
                          size: 18,
                          color: AppColors.lighterblue,
                        ),
                        SizedBox(width: 4),
                      ],
                    ),
                  ),
                ),
                Text(
                  "$comments",
                  style: const TextStyle(color: AppColors.textDark),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class CommunityPostDetailScreen extends StatefulWidget {
  const CommunityPostDetailScreen({
    super.key,
    required this.post,
    required this.currentUserId,
  });

  final Map<String, dynamic> post;
  final String currentUserId;

  @override
  State<CommunityPostDetailScreen> createState() => _CommunityPostDetailScreenState();
}

class _CommunityPostDetailScreenState extends State<CommunityPostDetailScreen> {
  bool _loading = true;
  String? _error;

  Map<String, dynamic> _post = {};
  List<Map<String, dynamic>> _comments = [];

  final TextEditingController _commentCtrl = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _post = Map<String, dynamic>.from(widget.post);
    _loadAll();
  }

  @override
  void dispose() {
    _commentCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final postId = (_post["id"] ?? 0) as int;

      final freshPost = await ApiService.fetchCommunityPostDetail(
        postId: postId,
      );

      final resComments = await ApiService.fetchPostComments(
        postId: postId,
        limit: 200,
        offset: 0,
      );

      final items = (resComments["items"] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .toList();

      setState(() {
        _post = freshPost;
        _comments = items;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _relativeTime(num? unixSeconds) {
    if (unixSeconds == null) return "";
    final dt = DateTime.fromMillisecondsSinceEpoch((unixSeconds * 1000).toInt());
    final diff = DateTime.now().difference(dt);

    if (diff.inSeconds < 60) return "just now";
    if (diff.inMinutes < 60) return "${diff.inMinutes} min ago";
    if (diff.inHours < 24) return "${diff.inHours} hours ago";
    if (diff.inDays < 7) return "${diff.inDays} days ago";
    final weeks = (diff.inDays / 7).floor();
    return "$weeks weeks ago";
  }

  Future<void> _sendComment() async {
    final text = _commentCtrl.text.trim();
    if (text.isEmpty || _sending) return;

    setState(() => _sending = true);

    try {
      final postId = (_post["id"] ?? 0) as int;

      final res = await ApiService.addPostComment(
        postId: postId,
        content: text,
      );

      // optimistic local append (author info minimal)
      _commentCtrl.clear();

      // refresh comment list to get author objects from backend
      await _loadAll();

      // update cached comment count from backend response if present
      setState(() {
        _post["comments"] = res["comments"] ?? _post["comments"];
      });
    } catch (e) {
      // simple error
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to send comment: $e")),
      );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final author = (_post["author"] as Map<String, dynamic>? ?? {});
    final authorName = (author["name"] ?? author["username"] ?? "Unknown").toString();

    return PopScope(
          canPop: false, // Prevents default pop so we can inject our data
          onPopInvoked: (bool didPop) {
            if (didPop) return;
            // Send the updated _post back on Android swipe-back/physical back button
            Navigator.pop(context, _post); 
          },
          child: Scaffold(
            backgroundColor: AppColors.background,
            appBar: AppBar(
              backgroundColor: AppColors.background,
              elevation: 0,
              iconTheme: const IconThemeData(color: AppColors.lighterblue),
              
              // 👉 2. Add the leading button for the visual AppBar back arrow
              leading: IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () {
                  // Send the updated _post back when the arrow is tapped
                  Navigator.pop(context, _post);
                },
              ),
              
              title: const Text(
                "Post",
                style: TextStyle(color: AppColors.titletext, fontWeight: FontWeight.w500),
              ),
            ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: RefreshIndicator(
                onRefresh: _loadAll,
                child: _loading
                    ? ListView(
                        padding: const EdgeInsets.all(20),
                        children: const [
                          SizedBox(height: 40),
                          Center(child: CircularProgressIndicator()),
                        ],
                      )
                    : (_error != null)
                        ? ListView(
                            padding: const EdgeInsets.all(20),
                            children: [
                              const SizedBox(height: 20),
                              Text(
                                "Couldn’t load post.",
                                style: const TextStyle(
                                  color: AppColors.textDark,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _error!,
                                style: TextStyle(color: AppColors.textDark.withOpacity(0.6)),
                              ),
                            ],
                          )
                        : ListView(
                            padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                            children: [
                              CommunityPostCard(
                                author: authorName,
                                time: _relativeTime(_post["date_created"] as num?),
                                content: (_post["content"] ?? "").toString(),
                                likes: (_post["likes"] ?? 0) as int,
                                comments: (_post["comments"] ?? 0) as int,
                                likedByMe: (_post["liked_by_me"] ?? false) as bool,
                                onCardTap: null,
                                onCommentTap: null,
                                onLikeTap: () async {
                                  final postId = (_post["id"] ?? 0) as int;
                                  final liked = (_post["liked_by_me"] ?? false) as bool;

                                  setState(() {
                                    _post["liked_by_me"] = !liked;
                                    _post["likes"] = (_post["likes"] ?? 0) + (liked ? -1 : 1);
                                  });

                                  try {
                                    if (!liked) {
                                      final r = await ApiService.likePost(
                                        postId: postId,
                                      );
                                      setState(() => _post["likes"] = r["likes"] ?? _post["likes"]);
                                    } else {
                                      final r = await ApiService.unlikePost(
                                        postId: postId,
                                      );
                                      setState(() => _post["likes"] = r["likes"] ?? _post["likes"]);
                                    }
                                  } catch (_) {
                                    setState(() {
                                      _post["liked_by_me"] = liked;
                                      _post["likes"] = (_post["likes"] ?? 0) + (liked ? 1 : -1);
                                    });
                                  }
                                },
                              ),
                              const SizedBox(height: 10),
                              Text(
                                "Comments",
                                style: TextStyle(
                                  color: AppColors.titletext.withOpacity(0.9),
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 10),
                              if (_comments.isEmpty)
                                Text(
                                  "No comments yet.",
                                  style: TextStyle(color: AppColors.textDark.withOpacity(0.7)),
                                )
                              else
                                ..._comments.map((c) => _CommentTile(comment: c)),
                            ],
                          ),
              ),
            ),

            // Input bar
            Container(
              padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
              decoration: BoxDecoration(
                color: AppColors.background,
                border: Border(
                  top: BorderSide(color: AppColors.blue.withOpacity(0.18)),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _commentCtrl,
                      minLines: 1,
                      maxLines: 4,
                      decoration: InputDecoration(
                        hintText: "Write a comment…",
                        hintStyle: TextStyle(color: AppColors.textDark.withOpacity(0.5)),
                        filled: true,
                        fillColor: AppColors.blue.withOpacity(0.18),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(16),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    height: 46,
                    width: 46,
                    child: ElevatedButton(
                      onPressed: _sending ? null : _sendComment,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.lighterblue,
                        foregroundColor: AppColors.background,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        padding: EdgeInsets.zero,
                      ),
                      child: _sending
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.send, size: 18),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
    );
  }}
class _CommentTile extends StatelessWidget {
  const _CommentTile({required this.comment});

  final Map<String, dynamic> comment;

  @override
  Widget build(BuildContext context) {
    final author = (comment["author"] as Map<String, dynamic>? ?? {});
    final name = (author["name"] ?? author["username"] ?? "User").toString();
    final first = name.isNotEmpty ? name[0].toUpperCase() : "?";

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.blue.withOpacity(0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.lighterblue.withOpacity(0.28),
            child: Text(
              first,
              style: const TextStyle(
                color: AppColors.titletext,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(
                    color: AppColors.titletext,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  (comment["content"] ?? "").toString(),
                  style: const TextStyle(
                    color: AppColors.textDark,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}



// import 'package:flutter/material.dart';
// import '../../../theme/app_colors.dart';
// import 'chat_screen.dart';
// import 'package:flutter_application_1/user_role.dart';

// class CommunityScreen extends StatelessWidget {
//   const CommunityScreen({super.key, required this.userRole});
//   final UserRole userRole;

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       backgroundColor: AppColors.background,

//       appBar: AppBar(
//         title: const Text(
//           'Community',
//           style: TextStyle(
//             color: AppColors.titletext,
//             fontWeight: FontWeight.w500,
//             fontSize: 20,
//           ),
//         ),
//         backgroundColor: AppColors.background,
//         elevation: 0,
//         automaticallyImplyLeading: false,
//         // --- LOGIC FIX HERE ---
//         actions: [
//           // Only show this button if the user is NOT a parent
//           if (userRole != UserRole.guardian) 
//             IconButton(
//               icon: const Icon(Icons.messenger, color: AppColors.lighterblue),
//               onPressed: () {
//                 Navigator.push(
//                   context,
//                   MaterialPageRoute(
//                     // Make sure this matches your actual file/class name
//                     builder: (context) => const MessagesScreen(), 
//                   ),
//                 );
//               },
//             ),
            
//           const SizedBox(width: 10),
//         ],
//       ),

//       body: SafeArea(
//         child: ListView(
//           padding: const EdgeInsets.all(20),
//           children: [
//             // Search
//             TextField(
//               decoration: InputDecoration(
//                 hintText: "Search topics...",
//                 hintStyle: const TextStyle(color: AppColors.lighterblue),
//                 prefixIcon: const Icon(Icons.search, color: AppColors.blue),
//                 filled: true,
//                 fillColor: AppColors.blue.withOpacity(0.3),
//                 border: OutlineInputBorder(
//                   borderRadius: BorderRadius.circular(12),
//                   borderSide: BorderSide.none,
//                 ),
//               ),
//             ),

//             const SizedBox(height: 16),

//             // Example post
//             const CommunityPostCard(
//               author: "Mindfulness Coach",
//               time: "2 hours ago",
//               content:
//                   "Reminder 🌱\n\nTake a slow breath in through your nose, "
//                   "hold for 4 seconds, and gently release.\n\n"
//                   "You’re doing better than you think.",
//               likes: 24,
//               comments: 5,
//             ),
//           ],
//         ),
//       ),
//     );
//   }
// }

// class CommunityPostCard extends StatelessWidget {
//   final String author;
//   final String time;
//   final String content;
//   final int likes;
//   final int comments;

//   const CommunityPostCard({
//     super.key,
//     required this.author,
//     required this.time,
//     required this.content,
//     required this.likes,
//     required this.comments,
//   });

//   @override
//   Widget build(BuildContext context) {
//     return Container(
//       margin: const EdgeInsets.only(bottom: 16),
//       padding: const EdgeInsets.all(16),
//       decoration: BoxDecoration(
//         color: AppColors.blue.withOpacity(0.25),
//         borderRadius: BorderRadius.circular(16),
//       ),
//       child: Column(
//         crossAxisAlignment: CrossAxisAlignment.start,
//         children: [
//           // Header
//           Row(
//             children: [
//               CircleAvatar(
//                 radius: 18,
//                 backgroundColor: AppColors.lighterblue,
//                 child: Text(
//                   author[0],
//                   style: const TextStyle(
//                     color: AppColors.background,
//                     fontWeight: FontWeight.bold,
//                   ),
//                 ),
//               ),
//               const SizedBox(width: 10),
//               Column(
//                 crossAxisAlignment: CrossAxisAlignment.start,
//                 children: [
//                   Text(
//                     author,
//                     style: const TextStyle(
//                       color: AppColors.textDark,
//                       fontWeight: FontWeight.w600,
//                     ),
//                   ),
//                   Text(
//                     time,
//                     style: TextStyle(
//                       color: AppColors.textDark.withOpacity(0.6),
//                       fontSize: 12,
//                     ),
//                   ),
//                 ],
//               ),
//             ],
//           ),

//           const SizedBox(height: 12),

//           // Content
//           Text(
//             content,
//             style: const TextStyle(
//               color: AppColors.textDark,
//               fontSize: 14,
//               height: 1.4,
//             ),
//           ),

//           const SizedBox(height: 12),

//           // Actions
//           Row(
//             children: [
//               Icon(Icons.favorite_border,
//                   size: 18, color: AppColors.lighterblue),
//               const SizedBox(width: 4),
//               Text("$likes",
//                   style: const TextStyle(color: AppColors.textDark)),
//               const SizedBox(width: 16),
//               Icon(Icons.chat_bubble_outline,
//                   size: 18, color: AppColors.lighterblue),
//               const SizedBox(width: 4),
//               Text("$comments",
//                   style: const TextStyle(color: AppColors.textDark)),
//             ],
//           ),
//         ],
//       ),
//     );
//   }
// }

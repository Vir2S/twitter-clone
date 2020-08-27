import sys

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Post, Comment, Preference
from .forms import NewCommentForm
from users.models import Follow, Profile


def is_users(post_user, logged_user):
    return post_user == logged_user


PAGINATION_COUNT = 3


class PostListView(LoginRequiredMixin, ListView):

    model = Post
    template_name = 'feed/home.html'
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = PAGINATION_COUNT

    def get_context_data(self, **kwargs):

        data = super().get_context_data(**kwargs)
        all_users = []
        data_counter = Post.objects.values('author') \
                           .annotate(author_count=Count('author')) \
                           .order_by('-author_count')[:6]

        for aux in data_counter:

            all_users.append(User.objects.filter(pk=aux['author']).first())

        # if Preference.objects.get(user = self.request.user):
        #     data['preference'] = True

        # else:
        #     data['preference'] = False

        data['preference'] = Preference.objects.all()
        data['all_users'] = all_users

        print(all_users, file=sys.stderr)

        return data

    def get_queryset(self):

        user = self.request.user
        qs = Follow.objects.filter(user=user)
        follows = [user]

        for obj in qs:

            follows.append(obj.follow_user)

        return Post.objects.filter(author__in=follows).order_by('-date_posted')


class UserPostListView(LoginRequiredMixin, ListView):

    model = Post
    template_name = 'feed/user_posts.html'
    context_object_name = 'posts'
    paginate_by = PAGINATION_COUNT

    def visible_user(self):
        return get_object_or_404(User, username=self.kwargs.get('username'))

    def get_context_data(self, **kwargs):

        visible_user = self.visible_user()
        logged_user = self.request.user

        print(logged_user.username == '', file=sys.stderr)

        if logged_user.username == '' or logged_user is None:
            can_follow = False

        else:
            can_follow = (
                    Follow.objects.filter(
                        user=logged_user,
                        follow_user=visible_user
                    ).count() == 0
            )

        data = super().get_context_data(**kwargs)

        data['user_profile'] = visible_user
        data['can_follow'] = can_follow

        return data

    def get_queryset(self):

        user = self.visible_user()

        return Post.objects.filter(author=user).order_by('-date_posted')

    def post(self, request, *args, **kwargs):

        if request.user.id is not None:

            follows_between = Follow.objects.filter(
                user=request.user,
                follow_user=self.visible_user()
            )

            if 'follow' in request.POST:
                new_relation = Follow(user=request.user, follow_user=self.visible_user())

                if follows_between.count() == 0:
                    new_relation.save()

            elif 'unfollow' in request.POST:

                if follows_between.count() > 0:
                    follows_between.delete()

        return self.get(self, request, *args, **kwargs)


class PostDetailView(DetailView):

    model = Post
    template_name = 'feed/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):

        data = super().get_context_data(**kwargs)
        comments_connected = Comment.objects.filter(post_connected=self.get_object()).order_by('-date_posted')

        data['comments'] = comments_connected
        data['form'] = NewCommentForm(instance=self.request.user)

        return data

    def post(self, request, *args, **kwargs):
        new_comment = Comment(content=request.POST.get('content'),
                              author=self.request.user,
                              post_connected=self.get_object())
        new_comment.save()

        return self.get(self, request, *args, **kwargs)


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):

    model = Post
    template_name = 'feed/post_delete.html'
    context_object_name = 'post'
    success_url = '/'

    def test_func(self):
        return is_users(self.get_object().author, self.request.user)


class PostCreateView(LoginRequiredMixin, CreateView):

    model = Post
    fields = ['content']
    template_name = 'feed/post_new.html'
    success_url = '/'

    def form_valid(self, form):

        form.instance.author = self.request.user

        return super().form_valid(form)

    def get_context_data(self, **kwargs):

        data = super().get_context_data(**kwargs)
        data['tag_line'] = 'Add a new post'

        return data


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):

    model = Post
    fields = ['content']
    template_name = 'feed/post_new.html'
    success_url = '/'

    def form_valid(self, form):

        form.instance.author = self.request.user

        return super().form_valid(form)

    def test_func(self):
        return is_users(self.get_object().author, self.request.user)

    def get_context_data(self, **kwargs):

        data = super().get_context_data(**kwargs)
        data['tag_line'] = 'Edit a post'

        return data


class FollowsListView(ListView):

    model = Follow
    template_name = 'feed/follow.html'
    context_object_name = 'follows'

    def visible_user(self):
        return get_object_or_404(User, username=self.kwargs.get('username'))

    def get_queryset(self):

        user = self.visible_user()

        return Follow.objects.filter(user=user).order_by('-date')

    def get_context_data(self, *, object_list=None, **kwargs):

        data = super().get_context_data(**kwargs)
        data['follow'] = 'follows'

        return data


class FollowersListView(ListView):

    model = Follow
    template_name = 'feed/follow.html'
    context_object_name = 'follows'

    def visible_user(self):
        return get_object_or_404(User, username=self.kwargs.get('username'))

    def get_queryset(self):

        user = self.visible_user()

        return Follow.objects.filter(follow_user=user).order_by('-date')

    def get_context_data(self, *, object_list=None, **kwargs):

        data = super().get_context_data(**kwargs)
        data['follow'] = 'followers'

        return data


# Like Functionality====================================================================================
@login_required
def post_preference(request, post_id, user_preference):

    if request.method == "POST":

        each_post = get_object_or_404(Post, id=post_id)

        obj = ''
        value_obj = ''

        try:
            obj = Preference.objects.get(user=request.user, post=each_post)

            value_obj = obj.value
            value_obj = int(value_obj)

            user_preference = int(user_preference)

            if value_obj != user_preference:

                obj.delete()

                u_pref = Preference()

                u_pref.user = request.user
                u_pref.post = each_post
                u_pref.value = user_preference

                if user_preference == 1 and value_obj != 1:

                    each_post.likes += 1
                    each_post.dislikes -= 1

                elif user_preference == 2 and value_obj != 2:

                    each_post.dislikes += 1
                    each_post.likes -= 1

                u_pref.save()
                each_post.save()

                context = {
                    'each_post': each_post,
                    'post_id': post_id
                }

                return redirect('feed-home')

            elif value_obj == user_preference:

                obj.delete()

                if user_preference == 1:

                    each_post.likes -= 1

                elif user_preference == 2:

                    each_post.dislikes -= 1

                each_post.save()

                context = {
                    'each_post': each_post,
                    'post_id': post_id
                }

                return redirect('feed-home')

        except Preference.DoesNotExist:

            u_pref = Preference()

            u_pref.user = request.user
            u_pref.post = each_post
            u_pref.value = user_preference

            user_preference = int(user_preference)

            if user_preference == 1:

                each_post.likes += 1

            elif user_preference == 2:

                each_post.dislikes += 1

            u_pref.save()
            each_post.save()

            context = {'post': each_post,
                       'post_id': post_id}

            return redirect('feed-home')

    else:
        each_post = get_object_or_404(Post, id=post_id)

        context = {
            'each_post': each_post,
            'post_id': post_id
        }

        return redirect('feed-home')

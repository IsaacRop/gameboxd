from rest_framework.pagination import CursorPagination


class StandardCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    page_size_query_param = "page_size"
    max_page_size = 100


class FeedCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    page_size_query_param = "page_size"
    max_page_size = 50


class GameLogCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-updated_at"
    page_size_query_param = "page_size"
    max_page_size = 100


class GameCursorPagination(CursorPagination):
    page_size = 20
    ordering = "title"
    page_size_query_param = "page_size"
    max_page_size = 100

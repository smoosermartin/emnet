import emnet.utils as utils
import os
import threading
from textual import on
from textual.app import App
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalScroll, Center, Middle, Horizontal, Vertical, Container
from textual.message import Message
from textual.widgets import Label, Input, Select, ProgressBar, DataTable, Markdown, TextArea, TabbedContent
from textual.reactive import reactive


QUERY_TYPE = ["By topic", "By file"]
COLUMNS = [('file',)]


class AppHeader(Center):

    def compose(self):
        gradient = Gradient.from_colors(
            "#881177",
            "#aa3355",
            "#cc6666",
            "#ee9944",
            "#eedd00",
            "#99dd55",
            "#44dd88",
            "#22ccbb",
            "#00bbcc",
            "#0099cc",
            "#3366bb",
            "#663399",
        )
        with Middle():
            yield Label("          e  m  n  e  t         ")
            yield ProgressBar(total=100, gradient=gradient, show_percentage=False, show_eta=False)
            yield Label("    a semantic search engine    ")


class SearchField(HorizontalGroup):

    def compose(self):
        yield Input(placeholder="Write topics ('economic sanctions') or file name ('Nahuatl.txt') and hit ENTER")


class SearchBar(HorizontalGroup):

    def compose(self):
        yield Select(((query_type, query_type) for query_type in QUERY_TYPE), id="query_type", allow_blank=False)
        yield SearchField()

    class Found(Message):
        def __init__(self, query, results):
            self.query = query
            self.results = results
            super().__init__()

    @on(Input.Submitted)
    def send_query(self):
        selected_type = self.query_one(Select)
        input = self.query_one(Input)
        query_type = selected_type.value
        query = input.value
        if query:
            search_results = utils.start_search(query_type, query)
            if search_results:
                self.post_message(self.Found(query, search_results))
            else:
                self.notify("No such file found.", severity="error")
        with input.prevent(Input.Submitted):
            input.value = ''


class LeftTab(Middle):
    def compose(self):
        yield Label("", id="results_header")
        yield Horizontal(DataTable(), id="results_table")
        yield Label("Notes")
        yield TextArea()


class FileViewer(Container):
    def compose(self):
        yield Label("Click on a file to see its contents", id="article_header")
        yield VerticalScroll(Markdown("", id="file_content"), classes="hidden")


class SearchResults(Horizontal):
    def compose(self):
        yield LeftTab()
        yield FileViewer()


    def on_data_table_cell_selected(self, message=DataTable.CellSelected):
        file = message.value
        name = file.replace(".txt", '').replace("_", " ")
        print(file)
        file_path = utils.CORPUS_PATH + os.sep + file
        with open(file_path, 'r', encoding="utf-8") as file:
            file_content = file.read()
        self.query_one(VerticalScroll).remove_class("hidden")
        self.query_one(Markdown).update(file_content)
        self.query_one("#article_header").update(f"{name}\n")


class AppBody(Vertical):
    def compose(self):
        yield SearchBar()
        yield SearchResults(classes="hidden")

    def on_search_bar_found(self, message: SearchBar.Found):
        results = message.results
        self.query_one(SearchResults).remove_class("hidden")
        self.query_one("#results_header").update(f"Results for \n'{message.query}':")
        table_body = SearchResults.query_one(self, DataTable)
        table_body.clear()
        table_body.add_rows(results[:])


class Engine(App):
    CSS_PATH = "emnet.tcss"

    def compose(self):
        yield AppHeader()
        yield AppBody()

    def on_mount(self) -> None:
        self.query_one(ProgressBar).update(progress=100)
        table = self.query_one(DataTable)
        table.add_columns(*COLUMNS[0])


def run_app():
    app = Engine()
    app.run()


def main():
    t1 = threading.Thread(target=utils.initialize_engine)
    t2 = threading.Thread(target=utils.load_model)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    run_app()


if __name__ == "__main__":
    main()

use iced::widget::{button, column, container, pick_list, row, scrollable, text, text_input};
use iced::{Element, Length, Task, Theme};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::fmt;
use std::fs::File;
use std::io::BufReader;

pub fn main() -> iced::Result {
    iced::application(DolphinDict::boot, DolphinDict::update, DolphinDict::view)
        .theme(DolphinDict::theme)
        .title("DolphinDict - Immersive Gloss Viewer & Reader")
        .run()
}

#[derive(Debug, Clone, Deserialize)]
struct Gloss {
    definition: String,
    examples: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
struct Token {
    w: String, // word
    l: String, // lemma
    c: bool,   // is_core
}

type Dictionary = BTreeMap<String, Gloss>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Language {
    Latin,
    Greek,
}

impl fmt::Display for Language {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Language::Latin => write!(f, "Latin"),
            Language::Greek => write!(f, "Ancient Greek"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ViewMode {
    Glossary,
    Reader,
}

impl fmt::Display for ViewMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ViewMode::Glossary => write!(f, "Glossary"),
            ViewMode::Reader => write!(f, "Reader"),
        }
    }
}

struct DolphinDict {
    latin_dict: Dictionary,
    greek_dict: Dictionary,
    current_language: Language,
    view_mode: ViewMode,
    search_query: String,
    selected_word: Option<String>,
    reader_tokens: Vec<Token>,
}

#[derive(Debug, Clone)]
enum Message {
    SearchChanged(String),
    WordSelected(String),
    LanguageSelected(Language),
    ViewModeSelected(ViewMode),
}

impl Default for DolphinDict {
    fn default() -> Self {
        let latin_dict = load_dictionary("dict.json");
        let greek_dict = load_dictionary("greek_dict.json");

        Self {
            latin_dict,
            greek_dict,
            current_language: Language::Latin,
            view_mode: ViewMode::Glossary,
            search_query: String::new(),
            selected_word: None,
            reader_tokens: Vec::new(),
        }
    }
}

fn load_dictionary(path: &str) -> Dictionary {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return BTreeMap::new(),
    };
    let reader = BufReader::new(file);

    let raw_dict: BTreeMap<String, serde_json::Value> = match serde_json::from_reader(reader) {
        Ok(d) => d,
        Err(_) => return BTreeMap::new(),
    };

    raw_dict
        .into_iter()
        .filter_map(|(word, value)| {
            serde_json::from_value::<Gloss>(value)
                .ok()
                .map(|gloss| (word, gloss))
        })
        .collect()
}

fn load_annotated_text(path: &str) -> Vec<Token> {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return Vec::new(),
    };
    let reader = BufReader::new(file);
    serde_json::from_reader(reader).unwrap_or_default()
}

impl DolphinDict {
    fn boot() -> (Self, Task<Message>) {
        (Self::default(), Task::none())
    }

    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::SearchChanged(query) => {
                self.search_query = query;
            }
            Message::WordSelected(word) => {
                self.selected_word = Some(word);
            }
            Message::LanguageSelected(language) => {
                if self.current_language != language {
                    self.current_language = language;
                    self.selected_word = None;
                    self.search_query = String::new();
                    self.reader_tokens = Vec::new();
                    self.view_mode = ViewMode::Glossary;
                }
            }
            Message::ViewModeSelected(mode) => {
                self.view_mode = mode;
                if mode == ViewMode::Reader && self.reader_tokens.is_empty() {
                    let path = match self.current_language {
                        Language::Latin => "book1.annotated.json",
                        Language::Greek => "Μένων.annotated.json",
                    };
                    self.reader_tokens = load_annotated_text(path);
                }
            }
        }
        Task::none()
    }

    fn theme(&self) -> Theme {
        Theme::Dark
    }

    fn view(&self) -> Element<'_, Message> {
        let dict = match self.current_language {
            Language::Latin => &self.latin_dict,
            Language::Greek => &self.greek_dict,
        };

        let lang_picker = pick_list(
            &[Language::Latin, Language::Greek][..],
            Some(self.current_language),
            Message::LanguageSelected,
        )
        .width(Length::Fill)
        .padding(5);

        let view_picker = pick_list(
            &[ViewMode::Glossary, ViewMode::Reader][..],
            Some(self.view_mode),
            Message::ViewModeSelected,
        )
        .width(Length::Fill)
        .padding(5);

        let sidebar_top = column![lang_picker, view_picker].spacing(10);

        let sidebar_content: Element<Message> = match self.view_mode {
            ViewMode::Glossary => {
                let search_input = text_input("Search words...", &self.search_query)
                    .on_input(Message::SearchChanged)
                    .padding(10);

                let filtered_words = dict.keys().filter(|word| {
                    word.to_lowercase()
                        .contains(&self.search_query.to_lowercase())
                });

                let mut word_list = column![].spacing(5).width(Length::Fill);
                for word in filtered_words {
                    let is_selected = self.selected_word.as_ref() == Some(word);

                    word_list = word_list.push(
                        button(text(word))
                            .on_press(Message::WordSelected(word.clone()))
                            .width(Length::Fill)
                            .style(if is_selected {
                                button::primary
                            } else {
                                button::secondary
                            }),
                    );
                }

                column![search_input, scrollable(container(word_list).padding(5))]
                    .spacing(10)
                    .into()
            }
            ViewMode::Reader => {
                if let Some(selected) = &self.selected_word {
                    if let Some(gloss) = dict.get(selected) {
                        let examples_iter = gloss
                            .examples
                            .iter()
                            .map(|ex| text(format!("• {}", ex)).into());

                        let examples = column(examples_iter).spacing(10);

                        scrollable(
                            column![
                                text(selected).size(30),
                                text(&gloss.definition).size(16),
                                text("Examples:").size(18),
                                examples,
                            ]
                            .spacing(15),
                        )
                        .into()
                    } else {
                        container(text(format!("No gloss found for: {}", selected)))
                            .padding(10)
                            .into()
                    }
                } else {
                    container(text("Click a word to see its gloss")).padding(10).into()
                }
            }
        };

        let sidebar = column![sidebar_top, sidebar_content]
            .spacing(20)
            .width(Length::Fixed(250.0));

        let main_content: Element<Message> = match self.view_mode {
            ViewMode::Glossary => {
                if let Some(selected) = &self.selected_word {
                    if let Some(gloss) = dict.get(selected) {
                        let examples_iter = gloss
                            .examples
                            .iter()
                            .map(|ex| text(format!("• {}", ex)).into());

                        let examples = column(examples_iter).spacing(10);

                        column![
                            text(selected).size(40),
                            text(&gloss.definition).size(20),
                            text("Examples:").size(25),
                            scrollable(examples),
                        ]
                        .spacing(20)
                        .padding(20)
                        .into()
                    } else {
                        column![text("Word not found")].padding(20).into()
                    }
                } else {
                    column![text("Select a word to view its gloss")].padding(20).into()
                }
            }
            ViewMode::Reader => {
                if self.reader_tokens.is_empty() {
                    container(text("Reader data not found. Run parse_text.py first."))
                        .center_x(Length::Fill)
                        .center_y(Length::Fill)
                        .width(Length::Fill)
                        .height(Length::Fill)
                        .into()
                } else {
                    let mut tokens_btns = Vec::new();
                    for token in &self.reader_tokens {
                        let is_selected = self.selected_word.as_ref() == Some(&token.l);
                        let has_gloss = dict.contains_key(&token.l);
                        
                        let word_btn = button(text(&token.w))
                            .on_press(Message::WordSelected(token.l.clone()))
                            .padding(2)
                            .style(if is_selected {
                                button::primary
                            } else if has_gloss {
                                button::text // highlight words with glosses
                            } else if token.c {
                                button::secondary // core vocab
                            } else {
                                button::text
                            });
                            
                        tokens_btns.push(word_btn.into());
                    }

                    scrollable(
                        container(
                            row(tokens_btns)
                                .spacing(5)
                                .wrap()
                        ).padding(20)
                    ).into()
                }
            }
        };

        container(row![sidebar, main_content].spacing(20))
            .width(Length::Fill)
            .height(Length::Fill)
            .padding(20)
            .into()
    }
}

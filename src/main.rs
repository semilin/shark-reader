use iced::widget::{button, checkbox, column, container, row, scrollable, text, text_input};
use iced::{Alignment, Element, Length, Task, Theme};
use serde::Deserialize;
use std::collections::{BTreeMap, HashSet};
use std::fmt;
use std::fs::{self, File};
use std::io::BufReader;

const COLOR_BG: iced::Color = iced::Color::from_rgb(0.10, 0.10, 0.18);
const COLOR_SURFACE: iced::Color = iced::Color::from_rgb(0.14, 0.14, 0.24);
const COLOR_PRIMARY: iced::Color = iced::Color::from_rgb(0.30, 0.80, 0.77);
const COLOR_PRIMARY_DARK: iced::Color = iced::Color::from_rgb(0.20, 0.60, 0.57);
const COLOR_TEXT: iced::Color = iced::Color::from_rgb(0.95, 0.95, 0.97);
const COLOR_TEXT_MUTED: iced::Color = iced::Color::from_rgb(0.65, 0.68, 0.75);

fn bg_container<'a, T: 'a>(content: impl Into<Element<'a, T>>) -> Element<'a, T> {
    container(content)
        .width(Length::Fill)
        .height(Length::Fill)
        .center_x(Length::Fill)
        .padding(40)
        .style(|_| container::Style {
            background: Some(iced::Background::Color(COLOR_BG)),
            ..container::Style::default()
        })
        .into()
}

pub fn main() -> iced::Result {
    iced::application(DolphinDict::boot, DolphinDict::update, DolphinDict::view)
        .theme(DolphinDict::theme)
        .title("DolphinDict - Immersive Reader")
        .run()
}

#[derive(Debug, Clone, Deserialize)]
struct Gloss {
    definition: String,
    examples: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "t")]
enum Token {
    #[serde(rename = "w")]
    Word { w: String, l: String },
    #[serde(rename = "p")]
    Punctuation { w: String },
    #[serde(rename = "n")]
    Newline,
    #[serde(rename = "s")]
    Speaker { w: String },
    #[serde(rename = "m")]
    Marker { w: String },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
enum WorkType {
    Poem,
    Dialogue,
    Prose,
}

#[derive(Debug, Clone, Deserialize)]
struct TextMetadata {
    title: String,
    author: String,
    language: Language,
    work_type: WorkType,
    #[serde(skip)]
    path: String,
}

#[derive(Debug, Clone, Deserialize)]
struct AnnotatedText {
    metadata: TextMetadata,
    tokens: Vec<Token>,
}

type Dictionary = BTreeMap<String, Gloss>;

#[derive(Debug, Clone)]
enum AppView {
    Library,
    Reader(TextMetadata),
    Glossary(Language),
}

struct DolphinDict {
    view: AppView,
    latin_dict: Dictionary,
    greek_dict: Dictionary,
    latin_core: HashSet<String>,
    greek_core: HashSet<String>,
    available_texts: Vec<TextMetadata>,

    // UI State
    search_query: String,
    filter_latin: bool,
    filter_greek: bool,

    // Reader State
    selected_word: Option<String>,
    reader_tokens: Vec<Token>,
    lemma_frequencies: BTreeMap<String, f64>,
}

#[derive(Debug, Clone)]
enum Message {
    SearchChanged(String),
    FilterLatinToggled(bool),
    FilterGreekToggled(bool),
    TextSelected(TextMetadata),
    BackToLibrary,
    OpenGlossary(Language),
    WordSelected(String),
}

impl Default for DolphinDict {
    fn default() -> Self {
        let latin_dict = load_dictionary("dictionaries/latin.json");
        let greek_dict = load_dictionary("dictionaries/greek.json");
        let latin_core = load_core_list("core_lists/latin-core-list.csv");
        let greek_core = load_core_list("core_lists/greek-core-list.csv");

        let mut available_texts = Vec::new();
        if let Ok(entries) = fs::read_dir("texts") {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("json") {
                    if let Ok(file) = File::open(&path) {
                        let reader = BufReader::new(file);
                        // We only need to peek at the metadata
                        if let Ok(data) = serde_json::from_reader::<_, serde_json::Value>(reader) {
                            if let Some(meta_val) = data.get("metadata") {
                                if let Ok(mut meta) =
                                    serde_json::from_value::<TextMetadata>(meta_val.clone())
                                {
                                    meta.path = path.to_string_lossy().into_owned();
                                    available_texts.push(meta);
                                }
                            }
                        }
                    }
                }
            }
        }

        Self {
            view: AppView::Library,
            latin_dict,
            greek_dict,
            latin_core,
            greek_core,
            available_texts,
            search_query: String::new(),
            filter_latin: true,
            filter_greek: true,
            selected_word: None,
            reader_tokens: Vec::new(),
            lemma_frequencies: BTreeMap::new(),
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

fn load_core_list(path: &str) -> HashSet<String> {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return HashSet::new(),
    };
    let mut rdr = csv::Reader::from_reader(file);
    rdr.records()
        .filter_map(|result| result.ok())
        .filter_map(|record| record.get(0).map(|s| s.to_lowercase()))
        .collect()
}

fn load_annotated_text(path: &str) -> (TextMetadata, Vec<Token>, BTreeMap<String, f64>) {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => panic!("Failed to open text file: {}", path),
    };
    let reader = BufReader::new(file);
    let mut data: AnnotatedText =
        serde_json::from_reader(reader).expect("Failed to parse annotated text");
    data.metadata.path = path.to_string();

    let tokens = data.tokens;
    let mut lemma_counts: BTreeMap<String, usize> = BTreeMap::new();
    let mut total_words = 0;

    for token in &tokens {
        if let Token::Word { w: _, l } = token {
            *lemma_counts.entry(l.clone()).or_insert(0) += 1;
            total_words += 1;
        }
    }

    let frequencies: BTreeMap<String, f64> = if total_words > 0 {
        lemma_counts
            .into_iter()
            .map(|(lemma, count)| {
                let percentage = (count as f64 / total_words as f64) * 100.0;
                (lemma, percentage)
            })
            .collect()
    } else {
        BTreeMap::new()
    };

    (data.metadata, tokens, frequencies)
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
            Message::FilterLatinToggled(on) => {
                self.filter_latin = on;
            }
            Message::FilterGreekToggled(on) => {
                self.filter_greek = on;
            }
            Message::TextSelected(text_meta) => {
                let (meta, tokens, frequencies) = load_annotated_text(&text_meta.path);
                self.reader_tokens = tokens;
                self.lemma_frequencies = frequencies;
                self.view = AppView::Reader(meta);
                self.selected_word = None;
            }
            Message::BackToLibrary => {
                self.view = AppView::Library;
                self.reader_tokens = Vec::new();
                self.selected_word = None;
                self.lemma_frequencies = BTreeMap::new();
            }
            Message::OpenGlossary(lang) => {
                self.view = AppView::Glossary(lang);
                self.selected_word = None;
                self.search_query = String::new();
            }
            Message::WordSelected(word) => {
                self.selected_word = Some(word);
            }
        }
        Task::none()
    }

    fn theme(&self) -> Theme {
        Theme::Dark
    }

    fn view(&self) -> Element<'_, Message> {
        match &self.view {
            AppView::Library => self.library_view(),
            AppView::Reader(meta) => self.reader_view(meta),
            AppView::Glossary(lang) => self.glossary_view(*lang),
        }
    }

    fn library_view(&self) -> Element<'_, Message> {
        let title = text("DolphinDict Library")
            .size(36)
            .style(|_| iced::widget::text::Style {
                color: Some(COLOR_PRIMARY),
            });

        let search_input = text_input("Search texts...", &self.search_query)
            .on_input(Message::SearchChanged)
            .padding(14)
            .width(Length::Fixed(400.0));

        let filters = row![
            checkbox(self.filter_latin)
                .label("Latin")
                .on_toggle(Message::FilterLatinToggled),
            checkbox(self.filter_greek)
                .label("Ancient Greek")
                .on_toggle(Message::FilterGreekToggled),
        ]
        .spacing(24);

        let mut text_list = column![].spacing(16).width(Length::Fill);

        let filtered_texts = self.available_texts.iter().filter(|t| {
            let matches_search = t
                .title
                .to_lowercase()
                .contains(&self.search_query.to_lowercase())
                || t.author
                    .to_lowercase()
                    .contains(&self.search_query.to_lowercase());
            let matches_lang = match t.language {
                Language::Latin => self.filter_latin,
                Language::Greek => self.filter_greek,
            };
            matches_search && matches_lang
        });

        for text_meta in filtered_texts {
            let item = button(
                row![
                    column![
                        text(&text_meta.title).size(20),
                        text(&text_meta.author)
                            .size(14)
                            .style(|_| iced::widget::text::Style {
                                color: Some(COLOR_TEXT_MUTED),
                            }),
                    ]
                    .width(Length::Fill),
                    text(format!("{}", text_meta.language)).size(12).style(|_| {
                        iced::widget::text::Style {
                            color: Some(COLOR_PRIMARY),
                        }
                    }),
                ]
                .padding(16)
                .align_y(Alignment::Center),
            )
            .on_press(Message::TextSelected(text_meta.clone()))
            .width(Length::Fill)
            .style(button::secondary);

            text_list = text_list.push(item);
        }

        let glossary_buttons = row![
            button("Latin Glossary").on_press(Message::OpenGlossary(Language::Latin)),
            button("Greek Glossary").on_press(Message::OpenGlossary(Language::Greek)),
        ]
        .spacing(24);

        bg_container(
            column![
                title,
                search_input,
                filters,
                scrollable(text_list).height(Length::Fill),
                glossary_buttons
            ]
            .spacing(24)
            .max_width(800.0)
            .align_x(Alignment::Center),
        )
    }

    fn reader_view<'a>(&'a self, meta: &'a TextMetadata) -> Element<'a, Message> {
        let dict = match meta.language {
            Language::Latin => &self.latin_dict,
            Language::Greek => &self.greek_dict,
        };

        let core_list = match meta.language {
            Language::Latin => &self.latin_core,
            Language::Greek => &self.greek_core,
        };

        let back_btn = button("← Library").on_press(Message::BackToLibrary);
        let header_text = column![
            text(&meta.title).size(24),
            text(&meta.author)
                .size(16)
                .style(|_| iced::widget::text::Style {
                    color: Some(COLOR_TEXT_MUTED),
                }),
        ];

        let header = row![back_btn, header_text]
            .spacing(20)
            .align_y(Alignment::Center);

        let mut reader_col = column![].spacing(16).width(Length::Fill);
        let mut current_row_tokens = Vec::new();
        let mut line_number = 0;

        for token in &self.reader_tokens {
            match token {
                Token::Word { w, l } => {
                    let is_selected = self.selected_word.as_ref() == Some(l);
                    let has_gloss = dict.contains_key(l);

                    let word_btn = button(text(w).size(18))
                        .on_press(Message::WordSelected(l.clone()))
                        .padding(4)
                        .style(if is_selected {
                            button::primary
                        } else if has_gloss {
                            button::text
                        } else {
                            button::text
                        });

                    current_row_tokens.push(word_btn.into());
                }
                Token::Punctuation { w } => {
                    current_row_tokens.push(text(w).into());
                }
                Token::Newline => {
                    line_number += 1;
                    let mut line_row = row![];

                    if meta.work_type == WorkType::Poem {
                        let num_str = if line_number % 5 == 0 {
                            format!("{}", line_number)
                        } else {
                            "".to_string()
                        };
                        line_row = line_row.push(
                            container(text(num_str).size(12).style(|_| {
                                iced::widget::text::Style {
                                    color: Some(COLOR_TEXT_MUTED),
                                }
                            }))
                            .width(Length::Fixed(30.0))
                            .align_x(Alignment::End)
                            .padding(5),
                        );
                    }

                    line_row = line_row.push(
                        row(std::mem::take(&mut current_row_tokens))
                            .spacing(5)
                            .wrap(),
                    );
                    reader_col = reader_col.push(line_row);
                }
                Token::Speaker { w } => {
                    if !current_row_tokens.is_empty() {
                        reader_col = reader_col.push(
                            row(std::mem::take(&mut current_row_tokens))
                                .spacing(5)
                                .wrap(),
                        );
                    }
                    reader_col = reader_col.push(text(w).size(22));
                }
                Token::Marker { w } => {
                    current_row_tokens.push(
                        text(w)
                            .size(12)
                            .style(|_| iced::widget::text::Style {
                                color: Some(COLOR_TEXT_MUTED),
                            })
                            .into(),
                    );
                }
            }
        }

        if !current_row_tokens.is_empty() {
            reader_col = reader_col.push(row(current_row_tokens).spacing(5).wrap());
        }

        let main_reader = scrollable(container(reader_col).padding(32));

        let sidebar: Element<Message> = if let Some(selected) = &self.selected_word {
            let is_core = core_list.contains(&selected.to_lowercase());
            let frequency = self.lemma_frequencies.get(selected).copied();
            let frequency_str = frequency.map(|f| format!("{:.1}%", f)).unwrap_or_default();
            let star = if is_core {
                " ★".to_string()
            } else {
                String::new()
            };

            if let Some(gloss) = dict.get(selected) {
                let examples_iter = gloss
                    .examples
                    .iter()
                    .map(|ex| text(format!("• {}", ex)))
                    .map(|t| t.into());

                let freq_element: Element<Message> = if !frequency_str.is_empty() {
                    text(frequency_str)
                        .size(14)
                        .style(|_: &Theme| iced::widget::text::Style {
                            color: Some(COLOR_TEXT_MUTED),
                        })
                        .into()
                } else {
                    text("").into()
                };

                scrollable(
                    column![
                        text(format!("{}{}", selected, star)).size(32).style(|_| {
                            iced::widget::text::Style {
                                color: Some(COLOR_PRIMARY),
                            }
                        }),
                        text(&gloss.definition).size(18),
                        freq_element,
                        text("Examples:")
                            .size(16)
                            .style(|_| iced::widget::text::Style {
                                color: Some(COLOR_TEXT_MUTED)
                            }),
                        column(examples_iter).spacing(12),
                    ]
                    .spacing(20),
                )
                .into()
            } else if is_core {
                let freq_element: Element<Message> = if !frequency_str.is_empty() {
                    text(frequency_str)
                        .size(14)
                        .style(|_: &Theme| iced::widget::text::Style {
                            color: Some(COLOR_TEXT_MUTED),
                        })
                        .into()
                } else {
                    text("").into()
                };

                scrollable(
                    column![
                        text(format!("{}{}", selected, star)).size(30),
                        text("Core vocabulary").size(16),
                        freq_element,
                    ]
                    .spacing(15),
                )
                .into()
            } else {
                let freq_element: Element<Message> = if !frequency_str.is_empty() {
                    text(frequency_str)
                        .size(14)
                        .style(|_: &Theme| iced::widget::text::Style {
                            color: Some(COLOR_TEXT_MUTED),
                        })
                        .into()
                } else {
                    text("").into()
                };

                scrollable(
                    column![
                        text(selected).size(30),
                        text("No gloss available").size(16),
                        freq_element,
                    ]
                    .spacing(15),
                )
                .into()
            }
        } else {
            container(text("Click a word to see its gloss"))
                .padding(10)
                .into()
        };

        bg_container(
            column![
                header,
                row![
                    main_reader.width(Length::Fill),
                    container(sidebar).width(Length::Fixed(350.0)).padding(24)
                ]
                .spacing(24)
            ]
            .padding(24),
        )
    }

    fn glossary_view(&self, lang: Language) -> Element<'_, Message> {
        let dict = match lang {
            Language::Latin => &self.latin_dict,
            Language::Greek => &self.greek_dict,
        };

        let back_btn = button("← Library").on_press(Message::BackToLibrary);
        let title =
            text(format!("{} Glossary", lang))
                .size(30)
                .style(|_| iced::widget::text::Style {
                    color: Some(COLOR_PRIMARY),
                });
        let header = row![back_btn, title].spacing(24).align_y(Alignment::Center);

        let search_input = text_input("Search words...", &self.search_query)
            .on_input(Message::SearchChanged)
            .padding(14);

        let filtered_words = dict.keys().filter(|word| {
            word.to_lowercase()
                .contains(&self.search_query.to_lowercase())
        });

        let mut word_list = column![].spacing(8).width(Length::Fixed(280.0));
        for word in filtered_words {
            let is_selected = self.selected_word.as_ref() == Some(word);
            word_list = word_list.push(
                button(text(word).size(16))
                    .on_press(Message::WordSelected(word.clone()))
                    .width(Length::Fill)
                    .padding(12)
                    .style(if is_selected {
                        button::primary
                    } else {
                        button::secondary
                    }),
            );
        }

        let content: Element<Message> = if let Some(selected) = &self.selected_word {
            if let Some(gloss) = dict.get(selected) {
                let examples_iter = gloss
                    .examples
                    .iter()
                    .map(|ex| text(format!("• {}", ex)).size(16))
                    .map(|t| t.into());
                column![
                    text(selected)
                        .size(36)
                        .style(|_| iced::widget::text::Style {
                            color: Some(COLOR_PRIMARY)
                        }),
                    text(&gloss.definition).size(20),
                    text("Examples:")
                        .size(18)
                        .style(|_| iced::widget::text::Style {
                            color: Some(COLOR_TEXT_MUTED)
                        }),
                    scrollable(column(examples_iter).spacing(12)),
                ]
                .spacing(24)
                .into()
            } else {
                text("Select a word").size(18).into()
            }
        } else {
            text("Select a word to view its gloss")
                .size(18)
                .style(|_| iced::widget::text::Style {
                    color: Some(COLOR_TEXT_MUTED),
                })
                .into()
        };

        bg_container(
            column![
                header,
                search_input,
                row![
                    scrollable(container(word_list).padding(8)),
                    container(content).padding(32).width(Length::Fill)
                ]
                .spacing(24)
            ]
            .padding(32),
        )
    }
}

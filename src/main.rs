use iced::widget::{button, column, container, row, scrollable, text, text_input};
use iced::{Alignment, Element, Length, Task, Theme};
use serde::Deserialize;
use std::collections::{BTreeMap, HashSet};
use std::fmt;

// WASM imports for fetching
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;
#[cfg(target_arch = "wasm32")]
use wasm_bindgen_futures::JsFuture;
#[cfg(target_arch = "wasm32")]
use web_sys::Response;

// Embedded resources - dictionaries and core lists stay embedded
const LATIN_DICT_JSON: &str = include_str!("../dictionaries/latin.json");
const GREEK_DICT_JSON: &str = include_str!("../dictionaries/greek.json");
const LATIN_CORE_CSV: &str = include_str!("../core_lists/latin-core-list.csv");
const GREEK_CORE_CSV: &str = include_str!("../core_lists/greek-core-list.csv");

// Text paths - content loaded dynamically in WASM, embedded in native builds
#[cfg(not(target_arch = "wasm32"))]
const TEXTS: &[(&str, &str)] = &[
    (
        "texts/Aeneid1.annotated.json",
        include_str!("../texts/Aeneid1.annotated.json"),
    ),
    (
        "texts/Apology.annotated.json",
        include_str!("../texts/Apology.annotated.json"),
    ),
    (
        "texts/Crito.annotated.json",
        include_str!("../texts/Crito.annotated.json"),
    ),
    (
        "texts/Meno.annotated.json",
        include_str!("../texts/Meno.annotated.json"),
    ),
];

#[cfg(target_arch = "wasm32")]
const TEXTS: &[(&str, &str)] = &[
    ("texts/Aeneid1.annotated.json", ""),
    ("texts/Apology.annotated.json", ""),
    ("texts/Crito.annotated.json", ""),
    ("texts/Meno.annotated.json", ""),
];

#[cfg(target_arch = "wasm32")]
async fn fetch_text(path: &str) -> Result<String, String> {
    use wasm_bindgen::JsCast;

    let window = web_sys::window().ok_or("No window available")?;

    // Construct full URL respecting <base> tag
    let document = window.document().ok_or("No document available")?;
    let base_uri = document
        .base_uri()
        .map_err(|_| "No base URI")?
        .ok_or("No base URI".to_string())?;
    let url = format!("{}/{}", base_uri.trim_end_matches('/'), path);

    let resp_value = JsFuture::from(window.fetch_with_str(&url))
        .await
        .map_err(|_| "Fetch failed")?;

    let resp: Response = resp_value.dyn_into().map_err(|_| "Invalid response")?;

    if !resp.ok() {
        return Err(format!("HTTP error: {}", resp.status()));
    }

    let text = JsFuture::from(resp.text().map_err(|_| "Failed to get text")?)
        .await
        .map_err(|_| "Failed to read response body")?;

    text.as_string().ok_or("Invalid text content".to_string())
}

#[cfg(target_arch = "wasm32")]
async fn fetch_text_task(text_meta: TextMetadata) -> Result<Vec<Token>, String> {
    let content = fetch_text(&text_meta.path).await?;
    let data: AnnotatedText =
        serde_json::from_str(&content).map_err(|_| "Failed to parse annotated text")?;
    Ok(data.tokens)
}

const COLOR_BG: iced::Color = iced::Color::from_rgb(0.10, 0.10, 0.18);
const COLOR_SURFACE: iced::Color = iced::Color::from_rgb(0.14, 0.14, 0.24);
const COLOR_PRIMARY: iced::Color = iced::Color::from_rgb(0.30, 0.80, 0.77);
const COLOR_PRIMARY_DARK: iced::Color = iced::Color::from_rgb(0.20, 0.60, 0.57);
const COLOR_TEXT: iced::Color = iced::Color::from_rgb(0.95, 0.95, 0.97);
const COLOR_TEXT_MUTED: iced::Color = iced::Color::from_rgb(0.65, 0.68, 0.75);

fn teal_button(_theme: &iced::Theme, _status: iced::widget::button::Status) -> button::Style {
    button::Style {
        background: Some(iced::Background::Color(COLOR_PRIMARY)),
        border: iced::Border::default(),
        text_color: COLOR_BG,
        ..Default::default()
    }
}

fn bordered_button(_theme: &iced::Theme, _status: iced::widget::button::Status) -> button::Style {
    button::Style {
        background: Some(iced::Background::Color(COLOR_SURFACE)),
        border: iced::Border {
            width: 2.0,
            color: COLOR_PRIMARY,
            radius: 8.0.into(),
            ..Default::default()
        },
        text_color: COLOR_TEXT,
        ..Default::default()
    }
}

fn selected_word_button(
    _theme: &iced::Theme,
    _status: iced::widget::button::Status,
) -> button::Style {
    button::Style {
        background: Some(iced::Background::Color(COLOR_BG)),
        border: iced::Border {
            width: 2.0,
            color: COLOR_PRIMARY,
            radius: 4.0.into(),
            ..Default::default()
        },
        text_color: COLOR_TEXT,
        ..Default::default()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum InterfaceLang {
    English,
    Latin,
    Greek,
}

impl InterfaceLang {
    fn next(self) -> Self {
        match self {
            InterfaceLang::English => InterfaceLang::Latin,
            InterfaceLang::Latin => InterfaceLang::Greek,
            InterfaceLang::Greek => InterfaceLang::English,
        }
    }

    fn to_language(self) -> Option<Language> {
        match self {
            InterfaceLang::English => None,
            InterfaceLang::Latin => Some(Language::Latin),
            InterfaceLang::Greek => Some(Language::Greek),
        }
    }
}

struct Translations {
    library_title: (&'static str, &'static str, &'static str),
    search_texts: (&'static str, &'static str, &'static str),
    click_word: (&'static str, &'static str, &'static str),
    glossary: (&'static str, &'static str, &'static str),
    search_words: (&'static str, &'static str, &'static str),
    back_to_library: (&'static str, &'static str, &'static str),
    core_vocabulary: (&'static str, &'static str, &'static str),
    no_gloss: (&'static str, &'static str, &'static str),
    examples: (&'static str, &'static str, &'static str),
    select_word: (&'static str, &'static str, &'static str),
    select_word_detail: (&'static str, &'static str, &'static str),
}

fn t(tuple: &(&'static str, &'static str, &'static str), lang: InterfaceLang) -> &'static str {
    match lang {
        InterfaceLang::English => tuple.0,
        InterfaceLang::Latin => tuple.1,
        InterfaceLang::Greek => tuple.2,
    }
}

static TRANSLATIONS: Translations = Translations {
    library_title: ("Library", "Bibliothēca", "Βιβλιοθήκη"),
    search_texts: (
        "Search texts...",
        "Textūs quaere...",
        "Ζήτει συγγράμματα...",
    ),
    click_word: (
        "Click a word to see its gloss",
        "Verbum tange ut interpretātiōnem videās",
        "Ἅψαι λέξεως ἵνα τὴν ἐξήγησιν ἴδῃς",
    ),
    glossary: ("Glossary", "Glossarium", "Γλωσσάριον"),
    search_words: ("Search words...", "Verba quaere...", "Ζήτει λέξεις..."),
    back_to_library: ("← Library", "← Bibliothēca", "← Βιβλιοθήκη"),
    core_vocabulary: (
        "Core vocabulary",
        "Vocābulārium commune",
        "Κοινὸν λεξιλόγιον",
    ),
    no_gloss: (
        "No gloss available",
        "Nulla interpretātiō",
        "Οὐκ ἔστιν ἐξήγησις",
    ),
    examples: ("Examples:", "Exempla:", "Παραδείγματα:"),
    select_word: ("Select a word", "Verbum ēlige", "Ἐπέλεξον λέξιν"),
    select_word_detail: (
        "Select a word to view its gloss",
        "Verbum ēlige ut interpretātiōnem videās",
        "Ἐπέλεξον λέξιν ἵνα τὴν ἐξήγησιν ἴδῃς",
    ),
};

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
    iced::application(SharkReader::boot, SharkReader::update, SharkReader::view)
        .theme(SharkReader::theme)
        .title("SharkReader - Immersive Reader")
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
            Language::Latin => write!(f, "Latīnē"),
            Language::Greek => write!(f, "Ἑλληνιστί"),
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

struct SharkReader {
    view: AppView,
    latin_dict: Dictionary,
    greek_dict: Dictionary,
    latin_core: HashSet<String>,
    greek_core: HashSet<String>,
    available_texts: Vec<TextMetadata>,

    // UI State
    search_query: String,
    interface_lang: InterfaceLang,

    // Reader State
    selected_word: Option<String>,
    reader_tokens: Vec<Token>,
    lemma_frequencies: BTreeMap<String, f64>,

    // Loading State
    is_loading: bool,
    loading_error: Option<String>,
}

#[derive(Debug, Clone)]
enum Message {
    SearchChanged(String),
    ToggleInterfaceLang,
    TextSelected(TextMetadata),
    #[cfg(target_arch = "wasm32")]
    TextLoaded(Result<(TextMetadata, Vec<Token>, BTreeMap<String, f64>), String>),
    BackToLibrary,
    OpenGlossary(Language),
    WordSelected(String),
}

impl Default for SharkReader {
    fn default() -> Self {
        let latin_dict = load_dictionary(LATIN_DICT_JSON);
        let greek_dict = load_dictionary(GREEK_DICT_JSON);
        let latin_core = load_core_list(LATIN_CORE_CSV);
        let greek_core = load_core_list(GREEK_CORE_CSV);

        let mut available_texts = Vec::new();
        #[cfg(not(target_arch = "wasm32"))]
        {
            for (path, content) in TEXTS {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(content) {
                    if let Some(meta_val) = data.get("metadata") {
                        if let Ok(mut meta) =
                            serde_json::from_value::<TextMetadata>(meta_val.clone())
                        {
                            meta.path = path.to_string();
                            available_texts.push(meta);
                        }
                    }
                }
            }
        }
        #[cfg(target_arch = "wasm32")]
        {
            // WASM: metadata is hardcoded since we can't parse embedded content
            available_texts = vec![
                TextMetadata {
                    title: "Aeneis, Prīmus Liber".to_string(),
                    author: "Publius Vergilius Marō".to_string(),
                    language: Language::Latin,
                    work_type: WorkType::Poem,
                    path: "texts/Aeneid1.annotated.json".to_string(),
                },
                TextMetadata {
                    title: "Ἀπολογία Σωκράτους".to_string(),
                    author: "Πλάτων".to_string(),
                    language: Language::Greek,
                    work_type: WorkType::Dialogue,
                    path: "texts/Apology.annotated.json".to_string(),
                },
                TextMetadata {
                    title: "Κρίτων".to_string(),
                    author: "Πλάτων".to_string(),
                    language: Language::Greek,
                    work_type: WorkType::Dialogue,
                    path: "texts/Crito.annotated.json".to_string(),
                },
                TextMetadata {
                    title: "Μένων".to_string(),
                    author: "Πλάτων".to_string(),
                    language: Language::Greek,
                    work_type: WorkType::Dialogue,
                    path: "texts/Meno.annotated.json".to_string(),
                },
            ];
        }

        Self {
            view: AppView::Library,
            latin_dict,
            greek_dict,
            latin_core,
            greek_core,
            available_texts,
            search_query: String::new(),
            interface_lang: InterfaceLang::English,
            selected_word: None,
            reader_tokens: Vec::new(),
            lemma_frequencies: BTreeMap::new(),
            is_loading: false,
            loading_error: None,
        }
    }
}

fn load_dictionary(content: &str) -> Dictionary {
    let raw_dict: BTreeMap<String, serde_json::Value> = match serde_json::from_str(content) {
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

fn load_core_list(content: &str) -> HashSet<String> {
    let mut rdr = csv::Reader::from_reader(content.as_bytes());
    rdr.records()
        .filter_map(|result| result.ok())
        .filter_map(|record| record.get(0).map(|s| s.to_lowercase()))
        .collect()
}

fn load_annotated_text(
    content: &str,
    path: String,
) -> (TextMetadata, Vec<Token>, BTreeMap<String, f64>) {
    let mut data: AnnotatedText =
        serde_json::from_str(content).expect("Failed to parse annotated text");
    data.metadata.path = path;

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

impl SharkReader {
    fn boot() -> (Self, Task<Message>) {
        (Self::default(), Task::none())
    }

    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::SearchChanged(query) => {
                self.search_query = query;
            }
            Message::ToggleInterfaceLang => {
                self.interface_lang = self.interface_lang.next();
            }
            Message::TextSelected(text_meta) => {
                #[cfg(not(target_arch = "wasm32"))]
                {
                    // Native: use embedded content
                    let content = TEXTS
                        .iter()
                        .find(|(p, _)| *p == text_meta.path)
                        .map(|(_, c)| *c)
                        .expect("Text not found in embedded resources");
                    let (meta, tokens, frequencies) = load_annotated_text(content, text_meta.path);
                    self.reader_tokens = tokens;
                    self.lemma_frequencies = frequencies;
                    self.view = AppView::Reader(meta);
                    self.selected_word = None;
                    self.loading_error = None;
                }
                #[cfg(target_arch = "wasm32")]
                {
                    // WASM: set loading state and dispatch async fetch
                    self.is_loading = true;
                    self.loading_error = None;
                    self.view = AppView::Reader(text_meta.clone());
                    self.selected_word = None;
                    return Task::perform(fetch_text_task(text_meta.clone()), move |result| {
                        Message::TextLoaded(
                            result
                                .map(|tokens| (text_meta.clone(), tokens, BTreeMap::new()))
                                .map_err(|e| e),
                        )
                    });
                }
            }
            #[cfg(target_arch = "wasm32")]
            Message::TextLoaded(result) => {
                self.is_loading = false;
                match result {
                    Ok((meta, tokens, frequencies)) => {
                        self.reader_tokens = tokens;
                        self.lemma_frequencies = frequencies;
                        self.view = AppView::Reader(meta);
                        self.loading_error = None;
                    }
                    Err(err) => {
                        self.loading_error = Some(err);
                        self.reader_tokens = Vec::new();
                    }
                }
            }
            Message::BackToLibrary => {
                self.view = AppView::Library;
                self.reader_tokens = Vec::new();
                self.selected_word = None;
                self.lemma_frequencies = BTreeMap::new();
                self.is_loading = false;
                self.loading_error = None;
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
        let lang_label = match self.interface_lang {
            InterfaceLang::English => "English",
            InterfaceLang::Latin => "Latīnē",
            InterfaceLang::Greek => "Ἑλληνιστί",
        };

        let title = text(t(&TRANSLATIONS.library_title, self.interface_lang))
            .size(36)
            .style(|_| iced::widget::text::Style {
                color: Some(COLOR_PRIMARY),
            });

        let search_input = text_input(
            t(&TRANSLATIONS.search_texts, self.interface_lang),
            &self.search_query,
        )
        .on_input(Message::SearchChanged)
        .padding(14)
        .width(Length::Fixed(400.0));

        let lang_toggle = button(text(lang_label).size(14))
            .on_press(Message::ToggleInterfaceLang)
            .padding(12)
            .style(teal_button);

        let mut text_list = column![].spacing(16).width(Length::Fill);

        let target_lang = self.interface_lang.to_language();

        let filtered_texts = self.available_texts.iter().filter(|t| {
            let matches_search = t
                .title
                .to_lowercase()
                .contains(&self.search_query.to_lowercase())
                || t.author
                    .to_lowercase()
                    .contains(&self.search_query.to_lowercase());
            let matches_lang = target_lang.map_or(true, |lang| t.language == lang);
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
            .style(bordered_button);

            text_list = text_list.push(item);
        }

        let glossary_buttons: Element<'_, Message> = match self.interface_lang {
            InterfaceLang::English => row![
                button("Latin Glossary")
                    .on_press(Message::OpenGlossary(Language::Latin))
                    .style(teal_button),
                button("Greek Glossary")
                    .on_press(Message::OpenGlossary(Language::Greek))
                    .style(teal_button),
            ]
            .spacing(24)
            .into(),
            InterfaceLang::Latin => button(text(t(&TRANSLATIONS.glossary, InterfaceLang::Latin)))
                .on_press(Message::OpenGlossary(Language::Latin))
                .style(teal_button)
                .into(),
            InterfaceLang::Greek => button(text(t(&TRANSLATIONS.glossary, InterfaceLang::Greek)))
                .on_press(Message::OpenGlossary(Language::Greek))
                .style(teal_button)
                .into(),
        };

        bg_container(
            column![
                title,
                row![search_input, lang_toggle].spacing(16),
                scrollable(text_list).height(Length::Fill),
                glossary_buttons,
            ]
            .spacing(24)
            .max_width(500.0)
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

        let back_btn = button(t(&TRANSLATIONS.back_to_library, self.interface_lang))
            .on_press(Message::BackToLibrary)
            .style(teal_button);
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
                    let _has_gloss = dict.contains_key(l);

                    let word_btn = button(text(w).size(18))
                        .on_press(Message::WordSelected(l.clone()))
                        .padding(4)
                        .style(if is_selected {
                            selected_word_button
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

        // Show loading, error, or content
        let main_reader: Element<Message> = if self.is_loading {
            container(
                column![
                    text("Loading...").size(24),
                    text("Fetching text from server").size(14).style(|_| {
                        iced::widget::text::Style {
                            color: Some(COLOR_TEXT_MUTED),
                        }
                    }),
                ]
                .spacing(12)
                .align_x(Alignment::Center),
            )
            .center(Length::Fill)
            .into()
        } else if let Some(err) = &self.loading_error {
            container(
                column![
                    text("Failed to load text")
                        .size(24)
                        .style(|_| iced::widget::text::Style {
                            color: Some(iced::Color::from_rgb(0.9, 0.3, 0.3)),
                        }),
                    text(err).size(14).style(|_| iced::widget::text::Style {
                        color: Some(COLOR_TEXT_MUTED),
                    }),
                ]
                .spacing(12)
                .align_x(Alignment::Center),
            )
            .center(Length::Fill)
            .into()
        } else {
            scrollable(container(reader_col).padding(32)).into()
        };

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
                        text(t(&TRANSLATIONS.examples, self.interface_lang))
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
                        text(t(&TRANSLATIONS.core_vocabulary, self.interface_lang)).size(16),
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
                        text(t(&TRANSLATIONS.no_gloss, self.interface_lang)).size(16),
                        freq_element,
                    ]
                    .spacing(15),
                )
                .into()
            }
        } else {
            container(text(t(&TRANSLATIONS.click_word, self.interface_lang)))
                .padding(10)
                .into()
        };

        bg_container(
            column![
                header,
                row![
                    main_reader,
                    container(sidebar).width(Length::Fixed(350.0)).padding(24)
                ]
                .spacing(24)
            ]
            .max_width(1200)
            .padding(24),
        )
    }

    fn glossary_view(&self, lang: Language) -> Element<'_, Message> {
        let dict = match lang {
            Language::Latin => &self.latin_dict,
            Language::Greek => &self.greek_dict,
        };

        let back_btn = button(t(&TRANSLATIONS.back_to_library, self.interface_lang))
            .on_press(Message::BackToLibrary)
            .style(teal_button);
        let title = text(format!(
            "{}",
            t(&TRANSLATIONS.glossary, self.interface_lang)
        ))
        .size(30)
        .style(|_| iced::widget::text::Style {
            color: Some(COLOR_PRIMARY),
        });
        let header = row![back_btn, title].spacing(24).align_y(Alignment::Center);

        let search_input = text_input(
            t(&TRANSLATIONS.search_words, self.interface_lang),
            &self.search_query,
        )
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
                        selected_word_button
                    } else {
                        bordered_button
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
                    text(t(&TRANSLATIONS.examples, self.interface_lang))
                        .size(18)
                        .style(|_| iced::widget::text::Style {
                            color: Some(COLOR_TEXT_MUTED)
                        }),
                    scrollable(column(examples_iter).spacing(12)),
                ]
                .spacing(24)
                .into()
            } else {
                text(t(&TRANSLATIONS.select_word, self.interface_lang))
                    .size(18)
                    .into()
            }
        } else {
            text(t(&TRANSLATIONS.select_word_detail, self.interface_lang))
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
                    scrollable(container(word_list).padding(32)).width(Length::Fixed(250.)),
                    container(content).padding(16).width(Length::Fill)
                ]
                .spacing(24)
            ]
            .max_width(1200)
            .padding(32),
        )
    }
}

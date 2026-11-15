//! Assistant hors ligne EasySolar 1600 : recherche par embeddings dans le manuel, puis réponse du modèle fine-tuné.
//! Même logique que rag.py, sans serveur : le manuel et les consignes sont compilés dans le binaire.
//! Usage : easysolar [questions.txt]            (sans fichier : une question par ligne sur l'entrée standard)
//!         easysolar --search [questions.txt]   (affiche seulement les pages trouvées)
//! Les modèles sont lus dans le dossier models/ à côté de l'exécutable, ou dans $EASYSOLAR_MODELS.
use llama_cpp_2::context::LlamaContext;
use llama_cpp_2::context::params::{LlamaContextParams, LlamaPoolingType};
use llama_cpp_2::llama_backend::LlamaBackend;
use llama_cpp_2::llama_batch::LlamaBatch;
use llama_cpp_2::model::LlamaModel;
use llama_cpp_2::model::params::LlamaModelParams;
use llama_cpp_2::sampling::LlamaSampler;
use std::error::Error;
use std::io::BufRead;
use std::num::NonZeroU32;
use std::path::PathBuf;

const MANUEL: &str = include_str!("../../manuel_fr.md");
const CONSIGNES: &str = include_str!("../../consignes.txt");
const CHAT_MODEL: &str = "LFM3-1.7B-easysolar-Q4_K_M.gguf";
const EMB_MODEL: &str = "Qwen3-Embedding-0.6B-Q8_0.gguf";
const TASK: &str = "Instruct: Given a user question about a solar inverter, retrieve the manual page that answers it\nQuery: ";
const TOP_K: usize = 3;
const MAX_TOKENS: usize = 300;
const N_CTX: u32 = 8192;

type R<T> = Result<T, Box<dyn Error>>;

/// Découpe le manuel en sections commençant par « ## » (pages et annexes), comme rag.py.
fn pages() -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for line in MANUEL.split_inclusive('\n') {
        if line.starts_with("## ") || out.is_empty() {
            out.push(String::new());
        }
        out.last_mut().unwrap().push_str(line);
    }
    out.retain(|p| !p.trim().is_empty());
    out
}

/// Paragraphes (séparés par des lignes vides) de plus de 40 caractères, préfixés du titre de leur page.
fn chunks(pages: &[String]) -> Vec<(usize, String)> {
    let mut out = Vec::new();
    for (i, page) in pages.iter().enumerate() {
        let title = page.lines().next().unwrap();
        let lines: Vec<&str> = page.lines().collect();
        for para in lines.split(|l| l.trim().is_empty()).map(|p| p.join("\n")) {
            if para.trim().chars().count() > 40 {
                out.push((i, format!("{title}\n{para}")));
            }
        }
    }
    out
}

fn context<'a>(model: &'a LlamaModel, backend: &LlamaBackend, embeddings: bool) -> R<LlamaContext<'a>> {
    let params = LlamaContextParams::default()
        .with_n_ctx(NonZeroU32::new(N_CTX))
        .with_n_batch(N_CTX)
        .with_n_ubatch(if embeddings { N_CTX } else { 512 })
        .with_embeddings(embeddings)
        .with_pooling_type(if embeddings { LlamaPoolingType::Last } else { LlamaPoolingType::Unspecified });
    Ok(model.new_context(backend, params)?)
}

/// Vecteur normalisé d'un texte (pooling sur le dernier token, comme llama-server --pooling last).
fn embed(ctx: &mut LlamaContext, model: &LlamaModel, text: &str) -> R<Vec<f32>> {
    let tokens = model.vocab().tokenize(text.as_bytes(), true, false);
    let mut batch = LlamaBatch::new(tokens.len(), 1);
    batch.add_sequence(&tokens, 0, false)?;
    ctx.clear_kv_cache();
    ctx.decode(&mut batch)?;
    let v = ctx.embeddings_seq_ith(0)?;
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    Ok(v.iter().map(|x| x / norm).collect())
}

/// Les k pages dont le meilleur paragraphe est le plus proche de la question.
fn search(query: &[f32], chunks: &[(usize, String)], vectors: &[Vec<f32>], n_pages: usize) -> Vec<usize> {
    let mut best = vec![f32::MIN; n_pages];
    for ((page, _), v) in chunks.iter().zip(vectors) {
        let score: f32 = query.iter().zip(v).map(|(a, b)| a * b).sum();
        best[*page] = best[*page].max(score);
    }
    let mut order: Vec<usize> = (0..n_pages).collect();
    order.sort_by(|a, b| best[*b].total_cmp(&best[*a]));
    order.truncate(TOP_K);
    order
}

/// Prompt LFM3 identique à celui de llama-server avec enable_thinking=false (vérifié via /apply-template).
fn prompt(question: &str, hits: &[usize], pages: &[String]) -> String {
    let mut sorted = hits.to_vec();
    sorted.sort();
    let extraits: Vec<&str> = sorted.iter().map(|i| pages[*i].as_str()).collect();
    format!(
        "<|startoftext|><|im_start|>system\n{CONSIGNES}\n=== EXTRAITS DU MANUEL ===\n{}\n=== FIN ===<|im_end|>\n<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n<think></think>",
        extraits.join("\n")
    )
}

/// Génère la réponse avec les réglages de rag.py (temp 0.1, top_k 50, top_p 0.1, repeat_penalty 1.05).
fn generate(ctx: &mut LlamaContext, model: &LlamaModel, prompt: &str) -> R<String> {
    let tokens = model.vocab().tokenize(prompt.as_bytes(), false, true);
    let mut batch = LlamaBatch::new(N_CTX as usize, 1);
    let last = tokens.len() - 1;
    for (i, t) in tokens.iter().enumerate() {
        batch.add(*t, i as i32, &[0], i == last)?;
    }
    ctx.clear_kv_cache();
    ctx.decode(&mut batch)?;
    let mut sampler = LlamaSampler::chain_simple([
        LlamaSampler::penalties(model.n_vocab(), 64, 1.05, 0.0, 0.0),
        LlamaSampler::top_k(50),
        LlamaSampler::top_p(0.1, 1),
        LlamaSampler::min_p(0.05, 1),
        LlamaSampler::temp(0.1),
        LlamaSampler::dist(1234),
    ]);
    let mut out = Vec::new();
    let mut pos = tokens.len() as i32;
    for _ in 0..MAX_TOKENS {
        let token = sampler.sample(ctx, batch.n_tokens() - 1);
        sampler.accept(token);
        if model.vocab().is_eog(token) {
            break;
        }
        out.extend(model.vocab().token_to_piece(token, false, None));
        batch.clear();
        batch.add(token, pos, &[0], true)?;
        ctx.decode(&mut batch)?;
        pos += 1;
    }
    Ok(String::from_utf8_lossy(&out).trim().to_string())
}

fn main() -> R<()> {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let search_only = args.iter().any(|a| a == "--search");
    args.retain(|a| a != "--search");
    let dir = match std::env::var_os("EASYSOLAR_MODELS") {
        Some(d) => PathBuf::from(d),
        None => std::env::current_exe()?.parent().unwrap().join("models"),
    };
    let input: Box<dyn BufRead> = match args.first() {
        Some(f) => Box::new(std::io::BufReader::new(std::fs::File::open(f)?)),
        None => Box::new(std::io::stdin().lock()),
    };

    llama_cpp_2::send_logs_to_tracing(llama_cpp_2::LogOptions::default().with_logs_enabled(false));
    let backend = LlamaBackend::init()?;
    let gpu = LlamaModelParams::default().with_n_gpu_layers(1000);
    let emb_model = LlamaModel::load_from_file(&backend, dir.join(EMB_MODEL), &gpu)?;
    let mut emb_ctx = context(&emb_model, &backend, true)?;
    let pages = pages();
    let chunks = chunks(&pages);
    let vectors = chunks.iter().map(|(_, c)| embed(&mut emb_ctx, &emb_model, c)).collect::<R<Vec<_>>>()?;
    let chat = if search_only { None } else { Some(LlamaModel::load_from_file(&backend, dir.join(CHAT_MODEL), &gpu)?) };
    let mut chat_ctx = chat.as_ref().map(|m| context(m, &backend, false)).transpose()?;

    for line in input.lines() {
        let question = line?.trim().to_string();
        if question.is_empty() {
            continue;
        }
        let hits = search(&embed(&mut emb_ctx, &emb_model, &format!("{TASK}{question}"))?, &chunks, &vectors, pages.len());
        let titles: Vec<&str> = hits.iter().map(|i| pages[*i].lines().next().unwrap().trim_start_matches("## ")).collect();
        match (&chat, &mut chat_ctx) {
            (Some(model), Some(ctx)) => {
                let answer = generate(ctx, model, &prompt(&question, &hits, &pages))?;
                println!("## {question}\n\n{answer}\n\n_(extraits : {})_\n", titles.join(", "));
            }
            _ => println!("{question} -> {}", titles.join(", ")),
        }
    }
    Ok(())
}

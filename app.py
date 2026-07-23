import streamlit as st
import requests
import unicodedata

def normalize_text(text):
    text = text.lower().strip()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

def fetch_doi_metadata_openalex(doi):
    url = f"https://api.openalex.org/works/doi:{doi}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('authorships', [])
    except requests.exceptions.RequestException:
        return None

# Web Sayfası Başlığı ve Ayarları
st.set_page_config(page_title="Akademik Atama Puan Hesaplayıcı", page_icon="")
st.title("Akademik Atama Puan Hesaplayıcı")
st.markdown("Makalenizin DOI numarasını ve isminizi girerek atama/teşvik puanınızı otomatik hesaplayın.")

# Kategoriler ve Puanları
puan_sozlugu = {
    "ilk %1": 30.0,
    "ilk %10": 15.0,
    "Q1": 10.0,
    "Q2": 8.0,
    "Q3": 4.0,
    "Q4": 2.0,
    "TR Dizin": 1.0 
}

# Kullanıcı Giriş Alanları
secim = st.selectbox("Makalenin Q Değerini / Kategorisini Seçiniz:", list(puan_sozlugu.keys()), index=2)
tam_puan = puan_sozlugu[secim]

doi_entry = st.text_input("DOI Numarasını Giriniz (Örn: 10.1016/j.polymer...):")
name_entry = st.text_input("İsminizi Giriniz (Sadece İsminiz veya Soyisminiz yeterli):")

if st.button("Yazarları Bul ve Puanı Hesapla", type="primary"):
    doi = doi_entry.strip()
    author_name = name_entry.strip()
    
    if not doi or not author_name:
        st.warning("Lütfen DOI ve İsim alanlarını eksiksiz doldurunuz.")
    else:
        with st.spinner("OpenAlex API üzerinden yazarlar taranıyor..."):
            authorships = fetch_doi_metadata_openalex(doi)
            
        if authorships is None:
            st.error("Hata: DOI bulunamadı veya API'ye ulaşılamadı. Lütfen formatı kontrol edin.")
        elif not authorships:
            st.error("Bu DOI numarasına ait yazar bilgisi bulunamadı.")
        else:
            target_normalized = normalize_text(author_name)
            toplam_sorumlu_sayisi = max(1, sum(1 for auth in authorships if auth.get('is_corresponding', False)))
            
            found = False
            position = -1
            is_corresponding = False
            
            n_gercek = len(authorships)
            n_hesap = min(n_gercek, 5) 
            
            for i, auth in enumerate(authorships):
                display_name = auth.get('author', {}).get('display_name', '')
                if target_normalized in normalize_text(display_name):
                    found = True
                    position = i + 1
                    is_corresponding = auth.get('is_corresponding', False) 
                    break
                    
            if not found:
                 st.error(f"'{author_name}' yazar listesinde bulunamadı.")
                 makale_yazarlari = [a.get('author', {}).get('display_name', '') for a in authorships]
                 st.info(f"Makaledeki Kayıtlı Yazarlar: {', '.join(makale_yazarlari)}")
            else:
                # --- PUANLAMA MANTIĞI ---
                puan = 0
                hesap_detayi = f"**Makale Kategorisi:** {secim} (Taban Puan: {tam_puan})\n\n"
                hesap_detayi += f"**Gerçek Yazar Sayısı:** {n_gercek}\n\n"
                hesap_detayi += f"**Yazar Sıranız:** {position}. Yazar\n\n"
                hesap_detayi += f"**Sorumlu Yazar (Corresponding):** {'Evet' if is_corresponding else 'Hayır'}\n\n"
                
                if is_corresponding or n_gercek >= 5:
                    hesap_detayi += f"**Toplam Sorumlu Yazar Sayısı:** {toplam_sorumlu_sayisi}\n\n"
                
                hesap_detayi += "---\n\n"
                
                if n_gercek <= 4:
                    puan = tam_puan
                    hesap_detayi += f"✔️ **Kural:** 4 veya daha az yazar (Tüm yazarlar tam puan alır).\n"
                else:
                    if position == 1 or is_corresponding:
                        ilk_yazar_puani = tam_puan * 0.8 if position == 1 else 0
                        sorumlu_puani = (tam_puan * 0.8) / toplam_sorumlu_sayisi if is_corresponding else 0
                        
                        if position == 1 and not is_corresponding:
                            puan = ilk_yazar_puani
                            hesap_detayi += f"✔️ **Kural:** 5+ yazar ve İlk Yazar (Taban Puan x 0.8).\n"
                        elif is_corresponding and not position == 1:
                            puan = sorumlu_puani
                            hesap_detayi += f"✔️ **Kural:** 5+ yazar ve Sorumlu Yazar ((Taban Puan x 0.8) / {toplam_sorumlu_sayisi} sorumlu).\n"
                        else:
                            puan = max(ilk_yazar_puani, sorumlu_puani)
                            hesap_detayi += f"✔️ **Kural:** Hem İlk Hem Sorumlu Yazar (En yüksek avantajlı puan uygulandı).\n"
                    else:
                        puan = (tam_puan * 2) / n_hesap
                        hesap_detayi += f"✔️ **Kural:** 5+ yazar, Ortak Yazar ((Taban Puan x 2) / {n_hesap} yazar sayısına bölündü).\n"
                        
                # Sonuçları Göster
                st.info(hesap_detayi)
                st.success(f"### HESAPLANAN ATAMA PUANI: {puan:.2f}")

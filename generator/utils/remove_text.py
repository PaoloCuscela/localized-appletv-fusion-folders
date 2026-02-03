import os
import cv2
import numpy as np
import warnings
from pathlib import Path

# Configura warnings per sopprimere output verbosi se necessario
warnings.filterwarnings("ignore")

# Cartelle
input_folder = "downloaded_images"
output_folder = "images_no_text"

def get_refined_mask(image, bbox):
    """
    Crea una maschera raffinata per il testo all'interno di una bounding box.
    Usa la sogliatura per distinguere il testo dallo sfondo.
    """
    (tl, tr, br, bl) = bbox
    x_min = max(0, int(min(tl[0], bl[0])))
    x_max = min(image.shape[1], int(max(tr[0], br[0])))
    y_min = max(0, int(min(tl[1], tr[1])))
    y_max = min(image.shape[0], int(max(bl[1], br[1])))
    
    # Estrai ROI (Region of Interest)
    roi = image[y_min:y_max, x_min:x_max]
    if roi.size == 0:
        return None, (x_min, y_min)
        
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Sogliatura Otsu per trovare il testo
    # Assumiamo che il testo abbia un contrasto rispetto allo sfondo
    # Proviamo sia normale che invertito e vediamo quale ha senso (in base ai bordi)
    _, binary = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Euristica: controlla i bordi della ROI. Se i bordi sono prevalentemente bianchi, 
    # allora lo sfondo è bianco e il testo è nero (quindi il testo è 0 in binary).
    # Dobbiamo avere il testo come bianco (255) nella maschera.
    
    # Estrai i pixel del bordo
    borders = np.concatenate([
        binary[0, :], binary[-1, :], binary[:, 0], binary[:, -1]
    ])
    percentage_white_border = np.sum(borders == 255) / borders.size
    
    if percentage_white_border > 0.5:
        # Lo sfondo è bianco (255), quindi il testo è nero (0). Invertiamo per avere maschera testo=255.
        mask_roi = cv2.bitwise_not(binary)
    else:
        # Lo sfondo è nero (0), il testo è bianco (255). Teniamo così.
        mask_roi = binary
        
    # Dilatiamo leggermente per coprire gli aliasing del font
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_roi = cv2.dilate(mask_roi, kernel, iterations=1)
    
    return mask_roi, (x_min, y_min)

def remove_text_from_image(reader, image_path, output_path):
    """Rimuove il testo e riempie trasparenze usando Inpainting"""
    try:
        # Carica immagine con alpha channel (RGBA) se presente
        img_raw = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            print(f"❌ Errore caricamento: {image_path}")
            return False

        # Gestione canali
        has_alpha = False
        if img_raw.ndim == 3 and img_raw.shape[2] == 4:
            has_alpha = True
            # Separa canali colore e alpha
            img_bgr = img_raw[:, :, :3]
            alpha_channel = img_raw[:, :, 3]
        elif img_raw.ndim == 3:
             # Immagine BGR standard
             img_bgr = img_raw
             alpha_channel = None
        else:
             # Immagine grayscale? Gestiamo come BGR
             img_bgr = cv2.cvtColor(img_raw, cv2.COLOR_GRAY2BGR)
             alpha_channel = None

        # --- Fase 1: Creazione Maschera Testo (OCR) ---
        # Usa easyocr su immagine BGR
        results = reader.readtext(img_bgr)
        
        full_mask = np.zeros(img_bgr.shape[:2], dtype="uint8")
        
        text_detected = False
        if results:
            text_detected = True
            for (bbox, text, prob) in results:
                mask_roi, (x, y) = get_refined_mask(img_bgr, bbox)
                
                if mask_roi is not None:
                    h, w = mask_roi.shape
                    # Aggiungi alla maschera globale
                    full_mask[y:y+h, x:x+w] = cv2.bitwise_or(full_mask[y:y+h, x:x+w], mask_roi)
        
        # --- Fase 2: Aggiunta Trasparenza alla Maschera ---
        if has_alpha:
             # Identifica aree trasparenti (alpha=0, o < soglia)
             # Vogliamo riempirle, quindi le aggiungiamo alla maschera di inpainting (valore 255)
             _, alpha_mask = cv2.threshold(alpha_channel, 0, 255, cv2.THRESH_BINARY_INV)
             
             # Se vogliamo essere più laschi, possiamo considerare trasparente anche alpha parziale
             # Ma per inpainting di solito vogliamo riempire dove manca informazione
             
             full_mask = cv2.bitwise_or(full_mask, alpha_mask)

        # Se non c'è niente da fare (nessun testo e nessuna trasparenza da riempire)
        if cv2.countNonZero(full_mask) == 0:
            if not text_detected:
                print(f"  ℹ️  Nessuna modifica necessaria per {os.path.basename(image_path)}")
            # Salviamo l'immagine originale (come BGR se vogliamo rimuovere trasparenza, o come era?)
            # Se la richiesta è "riempi le parti trasparenti", il risultato è opaco.
            # Quindi meglio salvare img_bgr se non c'era testo.
            # Se has_alpha era True ma maschera vuota (impossibile con il codice sopra se alpha tutto 255 -> mask 0), 
            # significa immagine opaca completa.
            cv2.imwrite(output_path, img_bgr)
            return True

        # Dilatazione finale globale per sicurezza
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        full_mask = cv2.dilate(full_mask, kernel, iterations=2)
        
        # Inpainting
        # Usiamo un raggio più ampio (5 o 7) per coprire meglio le feature
        # INPAINT_NS (Navier-Stokes) spesso dà transizioni più fluide sui gradienti rispetto a TELEA
        result = cv2.inpaint(img_bgr, full_mask, 5, cv2.INPAINT_NS)
        
        # Salva risultato (il risultato di inpaint è BGR, quindi opaco)
        cv2.imwrite(output_path, result)
        print(f"  ✅ Elaborazione completata: {os.path.basename(image_path)}")
        return True

    except Exception as e:
        print(f"❌ Errore elaborazione {image_path}: {e}")
        return False

def main():
    # Verifica esistenza input
    if not os.path.exists(input_folder):
        print(f"Cartella {input_folder} non trovata.")
        return

    # Crea output
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Importazione condizionale per gestire dipendenze
    try:
        import easyocr
    except ImportError:
        print("La libreria 'easyocr' non è installata.")
        print("Installala con: pip install easyocr opencv-python")
        return

    print("Caricamento modello OCR (potrebbe richiedere tempo)...")
    # gpu=False per compatibilità, True se disponibile (es. CUDA o MPS su Mac, ma easyocr ha supporto variabile per MPS)
    reader = easyocr.Reader(['en'], gpu=False) 
    
    files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    print(f"Trovate {len(files)} immagini.")

    for i, filename in enumerate(files, 1):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        
        print(f"[{i}/{len(files)}] Elaborazione {filename}...")
        remove_text_from_image(reader, input_path, output_path)
    
    print(f"\nFinito! Immagini salvate in '{output_folder}'")

if __name__ == "__main__":
    main()

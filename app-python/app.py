"""
Lanzador unico de la app — esto es lo que se corre en la expo, no los
scripts sueltos.

Muestra un menu con un boton por cada categoria que ya tiene modelo
entrenado. Al tocar un boton, abre la camara y reconoce en vivo SOLO
esa categoria; al apretar 'q' en la ventana de la camara, vuelve a este
menu para elegir otra.

Uso:
    python app.py
"""
import os
import tkinter as tk
from tkinter import messagebox

import config
import reconocer_en_vivo


def categorias_disponibles():
    return [c for c in config.CATEGORIAS if os.path.exists(config.ruta_modelo(c))]


def main():
    ventana = tk.Tk()
    ventana.title("Reconocimiento de senas LSA")
    ventana.geometry("360x420")
    ventana.configure(bg="#14181a")

    tk.Label(
        ventana, text="Elegi una categoria", font=("Segoe UI", 16, "bold"),
        bg="#14181a", fg="#eef2f1", pady=20,
    ).pack()

    disponibles = categorias_disponibles()

    if not disponibles:
        tk.Label(
            ventana,
            text="No hay ningun modelo entrenado todavia.\n\n"
                 "Corre primero, por cada categoria:\n"
                 "  extraer_landmarks.py --categoria X\n"
                 "  entrenar_modelo.py --categoria X",
            font=("Segoe UI", 10), bg="#14181a", fg="#9db0aa", justify="left",
        ).pack(padx=20)
    else:
        def iniciar(categoria):
            ventana.withdraw()
            try:
                reconocer_en_vivo.main(categoria)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la camara para '{categoria}':\n{e}")
            finally:
                ventana.deiconify()

        for categoria in disponibles:
            tk.Button(
                ventana, text=categoria.capitalize(), font=("Segoe UI", 13),
                bg="#35b892", fg="#0d2620", activebackground="#2ea080",
                relief="flat", padx=20, pady=12, width=20,
                command=lambda c=categoria: iniciar(c),
            ).pack(pady=8)

    tk.Button(
        ventana, text="Salir", font=("Segoe UI", 11),
        bg="#1e2528", fg="#eef2f1", relief="flat", padx=10, pady=6,
        command=ventana.destroy,
    ).pack(pady=(30, 10))

    ventana.mainloop()


if __name__ == "__main__":
    main()

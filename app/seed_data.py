"""
Popula o banco com dados de demonstração: ~100 produtos, ~50 clientes e
centenas de vendas espalhadas nos últimos 90 dias — útil para testar
dashboards, gráficos e o alerta de estoque baixo com volume realista.

ATENÇÃO: isso ADICIONA dados novos, não apaga o que já existe. Use em
ambiente de teste/demonstração, não misture com dados reais de produção.

Uso (dentro do container):
    docker compose -f docker-compose.prod.yml exec app python -m app.seed_data
"""

import random
from datetime import datetime, timedelta

from app.database import Base, SessionLocal, engine
from app import models

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela", "Heitor",
    "Isabela", "João", "Larissa", "Marcos", "Natália", "Otávio", "Patrícia",
    "Rafael", "Sandra", "Thiago", "Vanessa", "William", "Beatriz", "Carlos",
    "Débora", "Eduardo", "Fernanda", "Gustavo", "Helena", "Igor", "Juliana", "Lucas",
]

LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
    "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa",
]

# (nome, (preço mínimo, preço máximo))
PRODUCTS = [
    # Papelaria
    ("Caderno universitário 10 matérias", (18, 32)),
    ("Caderno brochura 96 folhas", (10, 18)),
    ("Caneta esferográfica azul", (1.5, 3.5)),
    ("Caneta esferográfica preta", (1.5, 3.5)),
    ("Caneta esferográfica vermelha", (1.5, 3.5)),
    ("Lápis grafite HB", (1, 2.5)),
    ("Lápis de cor (caixa 12)", (12, 25)),
    ("Borracha branca", (1.5, 3)),
    ("Apontador com depósito", (2.5, 6)),
    ("Régua 30cm", (3, 7)),
    ("Marca-texto", (3.5, 7)),
    ("Cola bastão", (4, 9)),
    ("Cola branca 90g", (3, 7)),
    ("Tesoura escolar", (6, 14)),
    ("Estojo simples", (15, 35)),
    ("Pasta plástica com elástico", (5, 12)),
    ("Post-it bloco 100 folhas", (4, 9)),
    ("Grampeador pequeno", (12, 28)),
    ("Caixa de grampos", (2, 5)),
    ("Corretivo líquido", (3, 7)),
    # Limpeza
    ("Detergente neutro 500ml", (2.5, 5)),
    ("Sabão em pó 1kg", (10, 22)),
    ("Sabão em barra (pacote c/5)", (6, 14)),
    ("Desinfetante 1L", (6, 13)),
    ("Álcool 70% 500ml", (7, 15)),
    ("Esponja multiuso (pacote c/3)", (4, 9)),
    ("Pano de chão", (6, 14)),
    ("Pano multiuso (pacote c/5)", (8, 18)),
    ("Vassoura", (15, 32)),
    ("Rodo 40cm", (14, 28)),
    ("Saco de lixo 30L (pacote)", (8, 18)),
    ("Saco de lixo 50L (pacote)", (10, 22)),
    ("Amaciante 1L", (9, 19)),
    ("Água sanitária 1L", (5, 11)),
    ("Limpa vidros 500ml", (6, 13)),
    ("Desengordurante 500ml", (7, 15)),
    ("Inseticida spray", (9, 20)),
    ("Papel toalha (pacote c/2)", (6, 13)),
    ("Papel higiênico (pacote c/12)", (18, 35)),
    ("Luva de borracha (par)", (7, 15)),
    # Alimentos não perecíveis
    ("Arroz 5kg", (22, 38)),
    ("Feijão 1kg", (7, 14)),
    ("Açúcar refinado 1kg", (4, 8)),
    ("Café torrado 500g", (12, 24)),
    ("Óleo de soja 900ml", (7, 14)),
    ("Macarrão espaguete 500g", (4, 9)),
    ("Sal refinado 1kg", (2, 5)),
    ("Molho de tomate 340g", (3, 7)),
    ("Biscoito recheado", (4, 9)),
    ("Farinha de trigo 1kg", (5, 10)),
    ("Achocolatado em pó 400g", (8, 16)),
    ("Bolacha água e sal", (3, 7)),
    ("Leite em pó 400g", (16, 30)),
    ("Extrato de tomate 340g", (4, 8)),
    ("Vinagre 750ml", (3, 6)),
    ("Milho de pipoca 500g", (5, 10)),
    ("Aveia em flocos 500g", (6, 12)),
    ("Gelatina em pó", (2, 5)),
    ("Suco em pó (caixa)", (3, 7)),
    ("Chá em saquinhos (caixa)", (6, 13)),
    # Eletrônicos básicos
    ("Pilha AA (par)", (5, 11)),
    ("Pilha AAA (par)", (5, 11)),
    ("Pilha 9V", (10, 20)),
    ("Cabo USB-C 1m", (15, 35)),
    ("Cabo Micro USB 1m", (12, 28)),
    ("Carregador de celular 20W", (35, 70)),
    ("Fone de ouvido com fio", (18, 45)),
    ("Fone de ouvido bluetooth", (60, 150)),
    ("Adaptador de tomada", (10, 22)),
    ("Lâmpada LED 9W", (8, 18)),
    ("Lâmpada LED 12W", (10, 22)),
    ("Extensão elétrica 3 tomadas", (25, 55)),
    ("Extensão elétrica 5 tomadas", (35, 70)),
    ("Pen drive 32GB", (30, 60)),
    ("Pen drive 64GB", (45, 85)),
    ("Mouse óptico USB", (28, 55)),
    ("Teclado USB simples", (40, 90)),
    ("Controle remoto universal", (25, 55)),
    ("Régua de tomadas com USB", (45, 95)),
    ("Powerbank 10000mAh", (60, 140)),
    # Casa e utilidades
    ("Jogo de panelas antiaderente", (120, 280)),
    ("Conjunto de talheres (12 peças)", (35, 80)),
    ("Toalha de banho", (25, 55)),
    ("Toalha de rosto", (12, 28)),
    ("Jogo de lençol casal", (45, 95)),
    ("Jogo de lençol solteiro", (35, 75)),
    ("Vela aromática", (12, 28)),
    ("Porta-retrato médio", (15, 35)),
    ("Organizador plástico multiuso", (18, 42)),
    ("Varal retrátil", (30, 65)),
    ("Cesto de roupa suja", (25, 55)),
    ("Tapete para banheiro", (20, 45)),
    ("Cortina de box", (30, 65)),
    ("Jogo americano (kit 4)", (20, 45)),
    ("Potes plásticos herméticos (kit 3)", (25, 55)),
    ("Escorredor de louça", (35, 75)),
    ("Prendedor de roupa (pacote c/20)", (5, 12)),
    ("Vassoura de pelo", (18, 38)),
    ("Balde plástico 10L", (12, 25)),
    ("Kit de pincéis para pintura", (15, 35)),
]

TARGET_SALES = 350
SALES_WINDOW_DAYS = 90


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Criando produtos...")
        products = []
        for name, (pmin, pmax) in PRODUCTS:
            price = round(random.uniform(pmin, pmax), 2)
            # ~15% dos produtos ficam com estoque baixo de propósito,
            # pra dar pra testar o alerta e os gráficos de "em falta".
            if random.random() < 0.15:
                stock = random.randint(0, 5)
            else:
                stock = random.randint(10, 200)
            product = models.Product(name=name, price=price, stock_quantity=stock)
            db.add(product)
            products.append(product)
        db.commit()
        for p in products:
            db.refresh(p)
        print(f"  {len(products)} produtos criados.")

        print("Criando clientes...")
        clients = []
        used_names = set()
        while len(clients) < 50:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            if full_name in used_names:
                continue
            used_names.add(full_name)

            ddd = random.choice(["61", "62", "11", "21", "31", "41", "51"])
            phone = f"{ddd}9{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
            email = (
                f"{first.lower()}.{last.lower()}@exemplo.com"
                if random.random() < 0.7
                else None
            )
            client = models.Client(name=full_name, phone=phone, email=email)
            db.add(client)
            clients.append(client)
        db.commit()
        for c in clients:
            db.refresh(c)
        print(f"  {len(clients)} clientes criados.")

        print("Criando vendas...")
        today = datetime.utcnow()
        available = [p for p in products if p.stock_quantity > 0]
        sales_created = 0
        attempts = 0

        while sales_created < TARGET_SALES and attempts < TARGET_SALES * 5 and available:
            attempts += 1

            num_items = random.choice([1, 1, 1, 2, 2, 3])
            chosen = random.sample(available, k=min(num_items, len(available)))

            items_data = []
            for product in chosen:
                qty = random.randint(1, min(3, product.stock_quantity))
                items_data.append((product, qty))

            sale_date = today - timedelta(
                days=random.randint(0, SALES_WINDOW_DAYS),
                hours=random.randint(8, 20),
                minutes=random.randint(0, 59),
            )
            client = random.choice(clients) if random.random() < 0.7 else None

            sale = models.Sale(
                client_id=client.id if client else None, total=0.0, created_at=sale_date
            )
            db.add(sale)
            db.flush()

            total = 0.0
            for product, qty in items_data:
                total += product.price * qty
                db.add(
                    models.SaleItem(
                        sale_id=sale.id,
                        product_id=product.id,
                        quantity=qty,
                        unit_price=product.price,
                    )
                )
                product.stock_quantity -= qty
                if product.stock_quantity <= 0:
                    available.remove(product)

            sale.total = total
            db.commit()
            sales_created += 1

        print(f"  {sales_created} vendas criadas (últimos {SALES_WINDOW_DAYS} dias).")
        print("Seed concluído com sucesso.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()

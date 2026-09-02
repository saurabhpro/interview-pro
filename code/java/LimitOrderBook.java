import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Objects;
import java.util.TreeMap;

/**
 * A single-instrument limit-order book.
 *
 * <p>{@link #match(Order)} is the only write operation. It first consumes the
 * best eligible resting orders on the opposite side and records one
 * {@link Fill} for every consumed slice. If the incoming order is only partly
 * filled, its remainder is appended to the FIFO queue at its limit price.</p>
 *
 * <p>Bids are indexed from highest to lowest price; asks from lowest to
 * highest. This makes the first map entry the best executable price. Orders at
 * the same price are held in an {@link ArrayDeque}, which gives price-time
 * priority without mutating the caller's immutable {@link Order}.</p>
 */
public final class LimitOrderBook {

    private final NavigableMap<Long, ArrayDeque<BookOrder>> bids =
        new TreeMap<>(Comparator.reverseOrder());
    private final NavigableMap<Long, ArrayDeque<BookOrder>> asks = new TreeMap<>();
    private final List<Fill> fills = new ArrayList<>();

    /**
     * Matches and, if necessary, rests one incoming order.
     *
     * <p>For an incoming buy, the algorithm repeatedly examines the lowest ask
     * while {@code askPrice <= buyLimit}. For an incoming sell it examines the
     * highest bid while {@code bidPrice >= sellLimit}. Each iteration creates a
     * fill of {@code min(incomingRemainder, restingRemainder)}, then removes a
     * fully consumed resting order or keeps its reduced remainder at the head
     * of its FIFO queue. A positive incoming remainder is appended to the
     * incoming side.</p>
     *
     * <p>If {@code F} fills consume {@code L} price levels and {@code P} price
     * levels are occupied, matching takes {@code O(F + L log P + log P)} time;
     * the final {@code log P} term is the possible insertion of a remainder.
     * The book stores {@code O(R)} resting orders and the retained fill history
     * stores {@code O(F)} objects.</p>
     *
     * @param incoming immutable order to match
     * @throws NullPointerException if {@code incoming} is {@code null}
     */
    public void match(Order incoming) {
        Objects.requireNonNull(incoming, "incoming order");

        if (incoming.side() == Side.BUY) {
            matchAgainst(incoming, asks, bids);
        } else {
            matchAgainst(incoming, bids, asks);
        }
    }

    /**
     * Returns an immutable snapshot of every fill produced so far, in match
     * order. The list is intentionally separate from {@link #match(Order)}:
     * matching may produce no fill, while callers can query the retained
     * history whenever they need it.
     *
     * <p>Creating the snapshot takes {@code O(F)} time and space for {@code F}
     * retained fills.</p>
     */
    public List<Fill> getFills() {
        return List.copyOf(fills);
    }

    private void matchAgainst(
        Order incoming,
        NavigableMap<Long, ArrayDeque<BookOrder>> oppositeBook,
        NavigableMap<Long, ArrayDeque<BookOrder>> ownBook
    ) {
        long incomingRemainder = incoming.quantity();

        while (incomingRemainder > 0 && !oppositeBook.isEmpty()) {
            Map.Entry<Long, ArrayDeque<BookOrder>> bestLevel = oppositeBook.firstEntry();
            long bestOppositePrice = bestLevel.getKey();

            if (!crosses(incoming.side(), incoming.price(), bestOppositePrice)) {
                break;
            }

            ArrayDeque<BookOrder> restingAtBestPrice = bestLevel.getValue();
            BookOrder resting = restingAtBestPrice.peekFirst();
            long filledQuantity = Math.min(incomingRemainder, resting.remainingQuantity);

            fills.add(new Fill(incoming.id(), resting.price(), filledQuantity));
            incomingRemainder -= filledQuantity;
            resting.remainingQuantity -= filledQuantity;

            if (resting.remainingQuantity == 0) {
                restingAtBestPrice.removeFirst();
                if (restingAtBestPrice.isEmpty()) {
                    oppositeBook.pollFirstEntry();
                }
            }
        }

        if (incomingRemainder > 0) {
            ownBook.computeIfAbsent(incoming.price(), ignored -> new ArrayDeque<>())
                .addLast(new BookOrder(incoming, incomingRemainder));
        }
    }

    private static boolean crosses(Side incomingSide, long limitPrice, long bestOppositePrice) {
        return incomingSide == Side.BUY
            ? limitPrice >= bestOppositePrice
            : limitPrice <= bestOppositePrice;
    }

    /** Buy/sell direction of an order. */
    public enum Side {
        BUY,
        SELL
    }

    /**
     * Immutable submission to the order book.
     *
     * @param id stable identifier supplied by the caller
     * @param side buy or sell
     * @param price limit price; matching never executes at a worse price
     * @param quantity positive quantity requested
     */
    public record Order(String id, Side side, long price, long quantity) {

        public Order {
            Objects.requireNonNull(id, "order id");
            Objects.requireNonNull(side, "order side");
            if (id.isBlank()) {
                throw new IllegalArgumentException("order id must not be blank");
            }
            if (price < 0) {
                throw new IllegalArgumentException("price must not be negative");
            }
            if (quantity <= 0) {
                throw new IllegalArgumentException("quantity must be positive");
            }
        }
    }

    /**
     * One completed slice of an incoming order.
     *
     * @param orderId identifier of the incoming order that received the fill
     * @param fillPrice price of the resting order that supplied the liquidity
     * @param quantityFilled quantity completed in this slice
     */
    public record Fill(String orderId, long fillPrice, long quantityFilled) {

        public Fill {
            Objects.requireNonNull(orderId, "order id");
            if (orderId.isBlank()) {
                throw new IllegalArgumentException("order id must not be blank");
            }
            if (fillPrice < 0) {
                throw new IllegalArgumentException("fill price must not be negative");
            }
            if (quantityFilled <= 0) {
                throw new IllegalArgumentException("filled quantity must be positive");
            }
        }
    }

    private static final class BookOrder {

        private final long price;
        private long remainingQuantity;

        private BookOrder(Order order, long remainingQuantity) {
            this.price = order.price();
            this.remainingQuantity = remainingQuantity;
        }

        private long price() {
            return price;
        }
    }
}

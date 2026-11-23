import { divIcon } from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { Link } from 'react-router-dom'

const shopPin = divIcon({
  className: 'shop-map-pin',
  html: '<span></span>',
  iconSize: [28, 36],
  iconAnchor: [14, 34],
  popupAnchor: [0, -32],
})

export default function ShopMap({ shops, center = [39.9204, 32.8549], zoom = 12 }) {
  return (
    <MapContainer className="shop-map" center={center} zoom={zoom} scrollWheelZoom={false}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {shops.map((shop) => (
        <Marker
          key={shop.id}
          position={[shop.latitude, shop.longitude]}
          icon={shopPin}
        >
          <Popup>
            <div className="map-popup">
              <strong>{shop.name}</strong>
              <span>{shop.distance_km != null ? `${shop.distance_km} km uzaklıkta` : shop.address}</span>
              <Link to={`/shops/${shop.id}`}>Dükkanı incele</Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
